from __future__ import annotations

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DocumentTooLargeForGenerationError
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.quality import GenerationQualityChecker
from backend.app.generation.rag_orchestrator import RagGenerationOrchestrator
from backend.app.generation.rag_orchestrator import build_default_rag_query
from backend.app.generation.rag_cache import build_document_hash
from backend.app.generation.rag_cache import build_rag_cache_key
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository
from backend.app.storage.rag_cache import FileSystemRagCacheRepository


class StubRagProvider:
    """Deterministic provider stub returning canned embeddings and quiz responses."""

    def __init__(
        self,
        *,
        embedding_dimension: int,
        structured_responses: list[StructuredGenerationResponse],
        embedding_model_name: str = "rag-embed",
    ) -> None:
        self._embedding_dimension = embedding_dimension
        self._embedding_model_name = embedding_model_name
        self._structured_responses = list(structured_responses)
        self.embedding_requests: list[EmbeddingRequest] = []
        self.structured_requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        raise AssertionError("healthcheck should not be called by rag orchestrator tests")

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.embedding_requests.append(request)
        vectors = tuple(
            self._encode_text(text, position) for position, text in enumerate(request.texts)
        )
        return EmbeddingResponse(model_name=self._embedding_model_name, vectors=vectors)

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.structured_requests.append(request)
        if not self._structured_responses:
            raise AssertionError("provider was called more times than expected")
        return self._structured_responses.pop(0)

    def _encode_text(self, text: str, position: int) -> tuple[float, ...]:
        if "Москва" in text:
            return self._make_vector(0)
        if "Санкт-Петербург" in text or "Питер" in text:
            return self._make_vector(1)
        if "Кемерово" in text:
            return self._make_vector(2)
        return self._make_vector(min(position, self._embedding_dimension - 1))

    def _make_vector(self, hot_index: int) -> tuple[float, ...]:
        return tuple(1.0 if index == hot_index else 0.0 for index in range(self._embedding_dimension))


def build_document(
    *,
    document_id: str = "doc-rag",
    text: str | None = None,
) -> DocumentRecord:
    if text is None:
        text = (
            "Москва — столица России и крупнейший по численности населения город страны.\n"
            "Санкт-Петербург — северная столица, культурный центр на Неве.\n"
            "Кемерово — административный центр Кузбасса, расположен в Сибири."
        )
    return DocumentRecord(
        document_id=document_id,
        filename="russia.txt",
        media_type="text/plain",
        file_size_bytes=len(text.encode("utf-8")),
        normalized_text=text,
        metadata={"text_length": len(text)},
    )


def build_rag_request(question_count: int = 2) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.RAG,
    )


def build_quiz_payload(question_count: int = 2) -> dict[str, object]:
    questions = [
        {
            "question_id": f"q-{index + 1}",
            "prompt": f"Вопрос про Москву номер {index + 1}?",
            "options": [
                {"option_id": "opt-1", "text": "Москва"},
                {"option_id": "opt-2", "text": "Санкт-Петербург"},
            ],
            "correct_option_index": 0,
            "explanation": {"text": "Столицей России является Москва."},
        }
        for index in range(question_count)
    ]
    return {
        "quiz_id": "quiz-rag-generated",
        "document_id": "doc-rag",
        "title": "Quiz about Russia",
        "version": 1,
        "last_edited_at": "2026-04-25T19:00:00Z",
        "questions": questions,
    }


def build_response(
    payload: dict[str, object],
    *,
    model_name: str = "local-chat",
    response_id: str = "rag-resp-1",
) -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name=model_name,
        content=payload,
        raw_response={"id": response_id, "choices": [{"index": 0}]},
    )


def build_orchestrator(
    tmp_path,
    provider: StubRagProvider,
    *,
    chunk_size: int = 80,
    chunk_overlap: int = 20,
    top_k: int = 2,
    max_context_chars: int = 200,
    max_document_chars: int | None = None,
    rag_cache_repository=None,
) -> tuple[
    RagGenerationOrchestrator,
    FileSystemDocumentRepository,
    FileSystemGenerationResultRepository,
]:
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    result_repository = FileSystemGenerationResultRepository(tmp_path)
    orchestrator = RagGenerationOrchestrator(
        document_repository=document_repository,
        quiz_repository=quiz_repository,
        generation_result_repository=result_repository,
        provider=provider,
        quality_checker=GenerationQualityChecker(),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        max_context_chars=max_context_chars,
        max_document_chars=max_document_chars,
        embedding_model_name="rag-embed",
        rag_cache_repository=rag_cache_repository,
    )
    return orchestrator, document_repository, result_repository


def build_expected_cache_key(
    document: DocumentRecord,
    *,
    chunk_size: int = 80,
    chunk_overlap: int = 20,
    embedding_model_name: str = "rag-embed",
) -> str:
    return build_rag_cache_key(
        document_hash=build_document_hash(document.normalized_text),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model_name=embedding_model_name,
    )


def test_build_default_rag_query_renders_request_metadata_in_russian() -> None:
    request = build_rag_request(question_count=5)

    query = build_default_rag_query(request)

    assert "5" in query
    assert "ru" in query
    assert "medium" in query
    assert "single_choice" in query
    assert "Создай" in query


def test_rag_orchestrator_generates_and_persists_quiz_from_cyrillic_document(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[build_response(build_quiz_payload(question_count=2))],
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    persisted = result_repository.get(result.quiz.quiz_id)
    assert persisted == result
    assert result.prompt_version == "rag-v1"
    assert result.model_name == "local-chat"
    assert result.quiz.document_id == "doc-rag"
    assert any("Москву" in question.prompt for question in result.quiz.questions)


def test_rag_orchestrator_chunks_document_and_embeds_chunks_plus_query(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[build_response(build_quiz_payload(question_count=2))],
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    chunk_request_texts = [
        text
        for embed_request in provider.embedding_requests[:-1]
        for text in embed_request.texts
    ]
    assert len(chunk_request_texts) >= 2
    assert any("Москва" in text for text in chunk_request_texts)
    query_request = provider.embedding_requests[-1]
    assert len(query_request.texts) == 1
    assert "Создай" in query_request.texts[0]


def test_rag_orchestrator_writes_cache_on_embedding_cache_miss(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[build_response(build_quiz_payload(question_count=2))],
    )
    cache_repository = FileSystemRagCacheRepository(tmp_path)
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path,
        provider,
        rag_cache_repository=cache_repository,
    )
    document = build_document()
    document_repository.save(document)

    orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    cached_entry = cache_repository.get(build_expected_cache_key(document))
    assert cached_entry.document_hash == build_document_hash(document.normalized_text)
    assert cached_entry.index_metadata["chunk_count"] >= 2
    assert cached_entry.embedded_chunks[0].chunk.text.startswith(document.normalized_text[:5])
    assert len(provider.embedding_requests) == 2


def test_rag_orchestrator_reuses_cached_chunk_embeddings_for_identical_document(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-1"),
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-2"),
        ],
    )
    cache_repository = FileSystemRagCacheRepository(tmp_path)
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path,
        provider,
        rag_cache_repository=cache_repository,
    )
    document_repository.save(build_document())

    first_result = orchestrator.generate("doc-rag", build_rag_request(question_count=2))
    second_result = orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    assert first_result.prompt_version == "rag-v1"
    assert second_result.prompt_version == "rag-v1"
    assert len(provider.embedding_requests) == 3
    assert len(provider.embedding_requests[0].texts) >= 2
    assert len(provider.embedding_requests[1].texts) == 1
    assert len(provider.embedding_requests[2].texts) == 1
    assert build_document().normalized_text[:5] in provider.structured_requests[1].user_prompt


def test_rag_orchestrator_misses_cache_when_document_text_changes(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-1"),
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-2"),
        ],
    )
    cache_repository = FileSystemRagCacheRepository(tmp_path)
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path,
        provider,
        rag_cache_repository=cache_repository,
    )
    document_repository.save(build_document())
    orchestrator.generate("doc-rag", build_rag_request(question_count=2))
    changed_text = build_document().normalized_text + "\nНовый раздел документа."
    document_repository.save(build_document(text=changed_text))

    orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    assert len(provider.embedding_requests) == 4
    assert len(provider.embedding_requests[0].texts) >= 2
    assert len(provider.embedding_requests[2].texts) >= 2


def test_rag_orchestrator_misses_cache_when_chunk_parameters_change(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-1"),
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-2"),
        ],
    )
    cache_repository = FileSystemRagCacheRepository(tmp_path)
    first_orchestrator, document_repository, _ = build_orchestrator(
        tmp_path,
        provider,
        chunk_size=80,
        chunk_overlap=20,
        rag_cache_repository=cache_repository,
    )
    second_orchestrator, _, _ = build_orchestrator(
        tmp_path,
        provider,
        chunk_size=100,
        chunk_overlap=20,
        rag_cache_repository=cache_repository,
    )
    document_repository.save(build_document())

    first_orchestrator.generate("doc-rag", build_rag_request(question_count=2))
    second_orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    assert len(provider.embedding_requests) == 4
    assert len(provider.embedding_requests[0].texts) >= 2
    assert len(provider.embedding_requests[2].texts) >= 2


def test_rag_orchestrator_raises_controlled_error_for_corrupted_cache_artifact(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-1"),
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-2"),
        ],
    )
    cache_repository = FileSystemRagCacheRepository(tmp_path)
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path,
        provider,
        rag_cache_repository=cache_repository,
    )
    document_repository.save(build_document())
    orchestrator.generate("doc-rag", build_rag_request(question_count=2))
    cached_files = list((tmp_path / "rag_cache").glob("*.json"))
    assert len(cached_files) == 1
    cached_files[0].write_text("{broken-json", encoding="utf-8")

    with pytest.raises(DomainValidationError, match="malformed"):
        orchestrator.generate("doc-rag", build_rag_request(question_count=2))


def test_rag_orchestrator_passes_retrieved_context_to_structured_generation_request(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[build_response(build_quiz_payload(question_count=2))],
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    assert len(provider.structured_requests) == 1
    structured_request = provider.structured_requests[0]
    assert "Москва" in structured_request.user_prompt
    assert "Retrieved context" in structured_request.user_prompt
    assert structured_request.schema_name == "quiz_payload"


def test_rag_orchestrator_uses_repair_prompt_after_quality_failure(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[
            build_response(build_quiz_payload(question_count=1), response_id="rag-resp-1"),
            build_response(build_quiz_payload(question_count=2), response_id="rag-resp-2"),
        ],
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    assert result.prompt_version == "repair-v1"
    assert len(provider.structured_requests) == 2
    assert "Repair" in provider.structured_requests[1].user_prompt or "repair" in provider.structured_requests[1].user_prompt.lower()


def test_rag_orchestrator_raises_after_repair_is_exhausted(tmp_path) -> None:
    provider = StubRagProvider(
        embedding_dimension=3,
        structured_responses=[
            build_response(build_quiz_payload(question_count=1), response_id="rag-resp-1"),
            build_response(build_quiz_payload(question_count=1), response_id="rag-resp-2"),
        ],
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    with pytest.raises(GenerationQualityError):
        orchestrator.generate("doc-rag", build_rag_request(question_count=2))

    assert len(provider.structured_requests) == 2


def test_rag_orchestrator_rejects_non_rag_generation_mode(tmp_path) -> None:
    provider = StubRagProvider(embedding_dimension=3, structured_responses=[])
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    direct_request = GenerationRequest(
        question_count=2,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )

    with pytest.raises(UnsupportedGenerationModeError, match="rag"):
        orchestrator.generate("doc-rag", direct_request)


def test_rag_orchestrator_guards_oversized_documents(tmp_path) -> None:
    long_text = "Москва. " * 1000
    provider = StubRagProvider(embedding_dimension=3, structured_responses=[])
    orchestrator, document_repository, _ = build_orchestrator(
        tmp_path, provider, max_document_chars=200
    )
    document_repository.save(build_document(text=long_text))

    with pytest.raises(DocumentTooLargeForGenerationError):
        orchestrator.generate("doc-rag", build_rag_request())


def test_rag_orchestrator_rejects_empty_document(tmp_path) -> None:
    provider = StubRagProvider(embedding_dimension=3, structured_responses=[])
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document(text=""))

    with pytest.raises(DomainValidationError, match="no content for retrieval"):
        orchestrator.generate("doc-rag", build_rag_request())


def test_rag_orchestrator_rejects_invalid_construction_arguments(tmp_path) -> None:
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    result_repository = FileSystemGenerationResultRepository(tmp_path)
    provider = StubRagProvider(embedding_dimension=3, structured_responses=[])

    with pytest.raises(ValueError, match="chunk_overlap"):
        RagGenerationOrchestrator(
            document_repository=document_repository,
            quiz_repository=quiz_repository,
            generation_result_repository=result_repository,
            provider=provider,
            quality_checker=GenerationQualityChecker(),
            chunk_size=20,
            chunk_overlap=20,
        )

    with pytest.raises(ValueError, match="top_k"):
        RagGenerationOrchestrator(
            document_repository=document_repository,
            quiz_repository=quiz_repository,
            generation_result_repository=result_repository,
            provider=provider,
            quality_checker=GenerationQualityChecker(),
            top_k=0,
        )
