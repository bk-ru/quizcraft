from __future__ import annotations

import json
import logging

from backend.app.core.modes import GenerationMode
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.orchestrator import DirectGenerationOrchestrator
from backend.app.generation.quality import GenerationQualityChecker
from backend.app.generation.request_builder import DirectGenerationRequestBuilder
from backend.app.generation.safe_logging import summarize_document_payload
from backend.app.generation.safe_logging import summarize_model_payload
from backend.app.prompts.registry import PromptRegistry
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository


class StubProvider:
    """Deterministic provider test double for logging assertions."""

    def __init__(self, response: StructuredGenerationResponse) -> None:
        self._response = response

    def healthcheck(self) -> ProviderHealthStatus:
        raise AssertionError("healthcheck should not be called in logging tests")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        return self._response

    def embed(self, request):
        raise AssertionError("embed should not be called in logging tests")


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=128,
        normalized_text="Highly confidential source text that must never appear in logs.",
        metadata={"text_length": 61},
    )


def build_response() -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name="local-model",
        content={
            "quiz_id": "quiz-generated",
            "document_id": "doc-1",
            "title": "Generated quiz",
            "version": 1,
            "last_edited_at": "2026-04-18T12:00:00Z",
            "questions": [
                {
                    "question_id": "q-1",
                    "prompt": "This private model response should not be logged verbatim.",
                    "options": [
                        {"option_id": "opt-1", "text": "Option A"},
                        {"option_id": "opt-2", "text": "Option B"},
                    ],
                    "correct_option_index": 0,
                    "explanation": {"text": "Private explanation."},
                }
            ],
        },
        raw_response={
            "id": "resp-1",
            "choices": [
                {
                    "message": {
                        "content": "This raw provider payload should not be logged verbatim."
                    }
                }
            ],
        },
    )


def build_request() -> GenerationRequest:
    return GenerationRequest(
        question_count=1,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )


def test_safe_logging_summaries_redact_document_and_model_content() -> None:
    document_summary = summarize_document_payload(build_document())
    model_summary = summarize_model_payload(build_response().content)

    rendered = json.dumps({"document": document_summary, "model": model_summary}, ensure_ascii=True)

    assert "Highly confidential source text" not in rendered
    assert "private model response" not in rendered.casefold()
    assert document_summary["text_length"] == len(build_document().normalized_text)
    assert model_summary["payload_length"] > 0
    assert "payload_digest" in model_summary


def test_orchestrator_logs_redacted_payload_summaries(caplog, tmp_path) -> None:
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    result_repository = FileSystemGenerationResultRepository(tmp_path)
    provider = StubProvider(build_response())
    orchestrator = DirectGenerationOrchestrator(
        document_repository=document_repository,
        quiz_repository=quiz_repository,
        generation_result_repository=result_repository,
        request_builder=DirectGenerationRequestBuilder(prompt_registry=PromptRegistry),
        provider=provider,
        quality_checker=GenerationQualityChecker(),
    )
    document = build_document()
    document_repository.save(document)

    with caplog.at_level(logging.INFO):
        orchestrator.generate(document.document_id, build_request())

    assert "Highly confidential source text" not in caplog.text
    assert "raw provider payload" not in caplog.text
    assert document.document_id in caplog.text
    assert "local-model" in caplog.text
