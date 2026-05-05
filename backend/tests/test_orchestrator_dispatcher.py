from __future__ import annotations

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import Quiz
from backend.app.generation.dispatcher import GenerationOrchestratorDispatcher
from backend.app.generation.mode_selector import DEFAULT_DIRECT_MAX_CHARS
from backend.app.generation.mode_selector import DEFAULT_RAG_MIN_CHARS


class _StubOrchestrator:
    """Захватывать dispatch-вызовы генерации и возвращать canned results."""

    def __init__(self, *, name: str, response: GenerationResult) -> None:
        self.name = name
        self._response = response
        self.calls: list[tuple[str, GenerationRequest]] = []

    def generate(self, document_id: str, generation_request: GenerationRequest) -> GenerationResult:
        self.calls.append((document_id, generation_request))
        return self._response


class _StubDocumentRepository:
    """Вернуть настроенный документ по id и записать обращения."""

    def __init__(self, documents: dict[str, DocumentRecord]) -> None:
        self._documents = dict(documents)
        self.requested_ids: list[str] = []

    def get(self, document_id: str) -> DocumentRecord:
        self.requested_ids.append(document_id)
        try:
            return self._documents[document_id]
        except KeyError:
            raise RepositoryNotFoundError("document", document_id)


def _build_document(document_id: str, *, length: int) -> DocumentRecord:
    text = "Я" * length
    return DocumentRecord(
        document_id=document_id,
        filename="ru.txt",
        media_type="text/plain",
        file_size_bytes=len(text.encode("utf-8")),
        normalized_text=text,
        metadata={"text_length": length},
    )


def _build_request(mode: GenerationMode) -> GenerationRequest:
    return GenerationRequest(
        question_count=2,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=mode,
    )


def _build_result(mode: GenerationMode) -> GenerationResult:
    quiz = Quiz(
        quiz_id="quiz-stub",
        document_id="doc-stub",
        title="Заглушка",
        version=1,
        last_edited_at="2026-04-25T20:00:00Z",
        questions=tuple(),
    )
    return GenerationResult(
        quiz=quiz,
        request=_build_request(mode),
        model_name="stub-model",
        prompt_version=f"{mode.value}-stub",
    )


def _build_dispatcher(
    *,
    documents: dict[str, DocumentRecord],
    direct_max_chars: int = DEFAULT_DIRECT_MAX_CHARS,
    rag_min_chars: int = DEFAULT_RAG_MIN_CHARS,
) -> tuple[GenerationOrchestratorDispatcher, _StubOrchestrator, _StubOrchestrator, _StubDocumentRepository]:
    direct = _StubOrchestrator(name="direct", response=_build_result(GenerationMode.DIRECT))
    rag = _StubOrchestrator(name="rag", response=_build_result(GenerationMode.RAG))
    repository = _StubDocumentRepository(documents)
    dispatcher = GenerationOrchestratorDispatcher(
        direct_orchestrator=direct,
        rag_orchestrator=rag,
        document_repository=repository,
        direct_max_chars=direct_max_chars,
        rag_min_chars=rag_min_chars,
    )
    return dispatcher, direct, rag, repository


def test_dispatcher_routes_short_direct_request_to_direct_orchestrator() -> None:
    document = _build_document("doc-direct", length=100)
    dispatcher, direct, rag, repository = _build_dispatcher(documents={"doc-direct": document})

    result = dispatcher.dispatch("doc-direct", _build_request(GenerationMode.DIRECT))

    assert result.prompt_version == "direct-stub"
    assert repository.requested_ids == ["doc-direct"]
    assert len(direct.calls) == 1
    assert rag.calls == []
    dispatched_request = direct.calls[0][1]
    assert dispatched_request.generation_mode is GenerationMode.DIRECT
    assert dispatched_request.question_count == 2
    assert dispatched_request.language == "ru"


def test_dispatcher_promotes_large_document_to_rag_orchestrator() -> None:
    """Документы >= DEFAULT_RAG_MIN_CHARS (30000) → RAG"""
    document = _build_document("doc-long", length=DEFAULT_RAG_MIN_CHARS)
    dispatcher, direct, rag, _ = _build_dispatcher(documents={"doc-long": document})

    result = dispatcher.dispatch("doc-long", _build_request(GenerationMode.DIRECT))

    assert result.prompt_version == "rag-stub"
    assert direct.calls == []
    assert len(rag.calls) == 1
    promoted_request = rag.calls[0][1]
    assert promoted_request.generation_mode is GenerationMode.RAG
    assert promoted_request.question_count == 2


def test_dispatcher_keeps_request_unchanged_when_resolved_mode_matches_requested() -> None:
    document = _build_document("doc-direct", length=10)
    dispatcher, direct, _, _ = _build_dispatcher(documents={"doc-direct": document})
    request = _build_request(GenerationMode.DIRECT)

    dispatcher.dispatch("doc-direct", request)

    forwarded_request = direct.calls[0][1]
    assert forwarded_request is request


def test_dispatcher_replaces_mode_when_promotion_occurs() -> None:
    """При promotion запрос заменяется на RAG"""
    document = _build_document("doc-long", length=DEFAULT_RAG_MIN_CHARS)
    dispatcher, _, rag, _ = _build_dispatcher(documents={"doc-long": document})
    request = _build_request(GenerationMode.DIRECT)

    dispatcher.dispatch("doc-long", request)

    promoted_request = rag.calls[0][1]
    assert promoted_request is not request
    assert request.generation_mode is GenerationMode.DIRECT
    assert promoted_request.generation_mode is GenerationMode.RAG


def test_dispatcher_routes_explicit_rag_request_below_threshold_to_rag_orchestrator() -> None:
    document = _build_document("doc-rag", length=50)
    dispatcher, direct, rag, _ = _build_dispatcher(documents={"doc-rag": document})

    dispatcher.dispatch("doc-rag", _build_request(GenerationMode.RAG))

    assert direct.calls == []
    assert len(rag.calls) == 1
    assert rag.calls[0][1].generation_mode is GenerationMode.RAG


def test_dispatcher_rejects_single_question_regen_mode() -> None:
    document = _build_document("doc-direct", length=10)
    dispatcher, _, _, _ = _build_dispatcher(documents={"doc-direct": document})

    with pytest.raises(UnsupportedGenerationModeError):
        dispatcher.dispatch("doc-direct", _build_request(GenerationMode.SINGLE_QUESTION_REGEN))


def test_dispatcher_propagates_repository_not_found() -> None:
    dispatcher, _, _, _ = _build_dispatcher(documents={})

    with pytest.raises(RepositoryNotFoundError):
        dispatcher.dispatch("doc-missing", _build_request(GenerationMode.DIRECT))


def test_dispatcher_uses_custom_thresholds_for_promotion() -> None:
    """Можно задать свои пороги"""
    document = _build_document("doc-cyr", length=11)
    dispatcher, direct, rag, _ = _build_dispatcher(
        documents={"doc-cyr": document},
        direct_max_chars=5,
        rag_min_chars=10,
    )

    dispatcher.dispatch("doc-cyr", _build_request(GenerationMode.DIRECT))

    # 11 >= 10 → RAG
    assert direct.calls == []
    assert len(rag.calls) == 1


def test_dispatcher_uses_cyrillic_normalized_length_for_selector() -> None:
    """Кириллические документы правильно оцениваются по длине"""
    document = DocumentRecord(
        document_id="doc-mixed",
        filename="mixed.txt",
        media_type="text/plain",
        file_size_bytes=100,
        normalized_text="Москва — столица России. " * 5,  # ~120 символов
        metadata={},
    )
    dispatcher, direct, rag, _ = _build_dispatcher(
        documents={"doc-mixed": document},
        direct_max_chars=50,
        rag_min_chars=100,
    )

    dispatcher.dispatch("doc-mixed", _build_request(GenerationMode.DIRECT))

    # ~120 >= 100 → RAG
    assert direct.calls == []
    assert len(rag.calls) == 1


@pytest.mark.parametrize("invalid_threshold", [0, -1])
def test_dispatcher_rejects_non_positive_rag_min_chars(invalid_threshold: int) -> None:
    document = _build_document("doc-direct", length=10)
    direct = _StubOrchestrator(name="direct", response=_build_result(GenerationMode.DIRECT))
    rag = _StubOrchestrator(name="rag", response=_build_result(GenerationMode.RAG))
    repository = _StubDocumentRepository({"doc-direct": document})

    with pytest.raises(ValueError):
        GenerationOrchestratorDispatcher(
            direct_orchestrator=direct,
            rag_orchestrator=rag,
            document_repository=repository,
            rag_min_chars=invalid_threshold,
        )


def test_dispatcher_rejects_boolean_rag_min_chars() -> None:
    direct = _StubOrchestrator(name="direct", response=_build_result(GenerationMode.DIRECT))
    rag = _StubOrchestrator(name="rag", response=_build_result(GenerationMode.RAG))
    repository = _StubDocumentRepository({})

    with pytest.raises(ValueError):
        GenerationOrchestratorDispatcher(
            direct_orchestrator=direct,
            rag_orchestrator=rag,
            document_repository=repository,
            rag_min_chars=True,  # type: ignore[arg-type]
        )


def test_dispatcher_rejects_non_positive_direct_max_chars() -> None:
    document = _build_document("doc-direct", length=10)
    direct = _StubOrchestrator(name="direct", response=_build_result(GenerationMode.DIRECT))
    rag = _StubOrchestrator(name="rag", response=_build_result(GenerationMode.RAG))
    repository = _StubDocumentRepository({"doc-direct": document})

    with pytest.raises(ValueError):
        GenerationOrchestratorDispatcher(
            direct_orchestrator=direct,
            rag_orchestrator=rag,
            document_repository=repository,
            direct_max_chars=0,
        )


def test_dispatcher_rejects_direct_max_not_less_than_rag_min() -> None:
    """direct_max_chars должен быть меньше rag_min_chars"""
    direct = _StubOrchestrator(name="direct", response=_build_result(GenerationMode.DIRECT))
    rag = _StubOrchestrator(name="rag", response=_build_result(GenerationMode.RAG))
    repository = _StubDocumentRepository({})

    with pytest.raises(ValueError, match="direct_max_chars must be less"):
        GenerationOrchestratorDispatcher(
            direct_orchestrator=direct,
            rag_orchestrator=rag,
            document_repository=repository,
            direct_max_chars=30000,
            rag_min_chars=15000,
        )


def test_dispatcher_exposes_threshold_properties() -> None:
    document = _build_document("doc-direct", length=10)
    dispatcher, _, _, _ = _build_dispatcher(
        documents={"doc-direct": document},
        direct_max_chars=5000,
        rag_min_chars=15000,
    )

    assert dispatcher.direct_max_chars == 5000
    assert dispatcher.rag_min_chars == 15000
