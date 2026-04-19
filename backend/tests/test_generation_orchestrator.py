from __future__ import annotations

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.orchestrator import DirectGenerationOrchestrator
from backend.app.generation.quality import GenerationQualityChecker
from backend.app.generation.request_builder import DirectGenerationRequestBuilder
from backend.app.prompts.registry import PromptRegistry
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository


class StubProvider:
    """Deterministic provider test double for orchestrator flows."""

    def __init__(self, responses: list[StructuredGenerationResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        raise AssertionError("healthcheck should not be called in orchestrator tests")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("provider was called more times than expected")
        return self._responses.pop(0)

    def embed(self, request):
        raise AssertionError("embed should not be called in orchestrator tests")


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=128,
        normalized_text="First source fact.\nSecond source fact.\nThird source fact.",
        metadata={"text_length": 56},
    )


def build_generation_request(question_count: int = 2) -> GenerationRequest:
    return GenerationRequest(
        question_count=question_count,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )


def build_payload(question_count: int = 2) -> dict[str, object]:
    questions = [
        {
            "question_id": f"q-{index + 1}",
            "prompt": f"Question {index + 1}?",
            "options": [
                {"option_id": "opt-1", "text": "Option A"},
                {"option_id": "opt-2", "text": "Option B"},
            ],
            "correct_option_index": 0,
            "explanation": {"text": f"Explanation {index + 1}."},
        }
        for index in range(question_count)
    ]
    return {
        "quiz_id": "quiz-generated",
        "document_id": "doc-1",
        "title": "Generated quiz",
        "version": 1,
        "last_edited_at": "2026-04-18T12:00:00Z",
        "questions": questions,
    }


def build_response(
    payload: dict[str, object],
    *,
    model_name: str = "local-model",
    response_id: str = "resp-1",
) -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name=model_name,
        content=payload,
        raw_response={"id": response_id, "choices": [{"index": 0}]},
    )


def build_orchestrator(tmp_path, provider: StubProvider) -> tuple[
    DirectGenerationOrchestrator,
    FileSystemDocumentRepository,
    FileSystemGenerationResultRepository,
]:
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    result_repository = FileSystemGenerationResultRepository(tmp_path)
    orchestrator = DirectGenerationOrchestrator(
        document_repository=document_repository,
        quiz_repository=quiz_repository,
        generation_result_repository=result_repository,
        request_builder=DirectGenerationRequestBuilder(prompt_registry=PromptRegistry),
        provider=provider,
        quality_checker=GenerationQualityChecker(),
    )
    return orchestrator, document_repository, result_repository


def test_direct_generation_orchestrator_persists_generation_result_on_success(tmp_path) -> None:
    provider = StubProvider([build_response(build_payload())])
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request())
    persisted = result_repository.get(result.quiz.quiz_id)

    assert result.prompt_version == "direct-v1"
    assert result.model_name == "local-model"
    assert result.quiz.version == 1
    assert result.quiz.last_edited_at.endswith("Z")
    assert persisted == result
    assert len(provider.requests) == 1


def test_direct_generation_orchestrator_uses_repair_prompt_after_quality_failure(tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload(question_count=1), response_id="resp-1"),
            build_response(build_payload(question_count=2), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, _ = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    result = orchestrator.generate("doc-1", build_generation_request(question_count=2))

    assert result.prompt_version == "repair-v1"
    assert len(provider.requests) == 2
    assert "question count" in provider.requests[1].user_prompt
    assert "\"questions\"" in provider.requests[1].user_prompt


def test_direct_generation_orchestrator_raises_after_repair_is_exhausted(tmp_path) -> None:
    invalid_payload = build_payload(question_count=1)
    provider = StubProvider(
        [
            build_response(invalid_payload, response_id="resp-1"),
            build_response(dict(invalid_payload), response_id="resp-2"),
        ]
    )
    orchestrator, document_repository, result_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    with pytest.raises(GenerationQualityError, match="question count"):
        orchestrator.generate("doc-1", build_generation_request(question_count=2))

    assert len(provider.requests) == 2
    with pytest.raises(RepositoryNotFoundError):
        result_repository.get("quiz-generated")
