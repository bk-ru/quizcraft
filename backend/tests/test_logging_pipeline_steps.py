from __future__ import annotations

import logging

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import GenerationQualityError
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
    """Deterministic provider test double for pipeline logging flows."""

    def __init__(self, responses: list[StructuredGenerationResponse]) -> None:
        self._responses = list(responses)

    def healthcheck(self) -> ProviderHealthStatus:
        raise AssertionError("healthcheck should not be called in pipeline logging tests")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        if not self._responses:
            raise AssertionError("provider was called more times than expected")
        return self._responses.pop(0)

    def embed(self, request):
        raise AssertionError("embed should not be called in pipeline logging tests")


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-ru-1",
        filename="лекция.txt",
        media_type="text/plain",
        file_size_bytes=128,
        normalized_text="Первый русский факт.\nВторой русский факт.",
        metadata={"text_length": 41},
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
            "prompt": f"Какой факт указан под номером {index + 1}?",
            "options": [
                {"option_id": "opt-1", "text": "Русский факт"},
                {"option_id": "opt-2", "text": "Лишний вариант"},
            ],
            "correct_option_index": 0,
            "explanation": {"text": "Ответ взят из русского документа."},
        }
        for index in range(question_count)
    ]
    return {
        "quiz_id": "quiz-ru-1",
        "document_id": "doc-ru-1",
        "title": "Квиз по русскому документу",
        "version": 1,
        "last_edited_at": "2026-04-23T12:00:00Z",
        "questions": questions,
    }


def build_response(payload: dict[str, object], response_id: str) -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name="local-model",
        content=payload,
        raw_response={"id": response_id},
    )


def build_orchestrator(
    tmp_path,
    provider: StubProvider,
) -> tuple[DirectGenerationOrchestrator, FileSystemDocumentRepository]:
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
    return orchestrator, document_repository


def generation_events(caplog) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if getattr(record, "generation_event", None) == "pipeline_step"
    ]


def event_pairs(caplog) -> list[tuple[str, str]]:
    return [
        (record.generation_step, record.generation_status)
        for record in generation_events(caplog)
    ]


def test_orchestrator_logs_success_pipeline_steps_with_redacted_russian_payloads(caplog, tmp_path) -> None:
    provider = StubProvider([build_response(build_payload(), "resp-1")])
    orchestrator, document_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    with caplog.at_level(logging.INFO):
        result = orchestrator.generate("doc-ru-1", build_generation_request())

    assert result.quiz.title == "Квиз по русскому документу"
    assert event_pairs(caplog) == [
        ("parse", "queued"),
        ("parse", "running"),
        ("parse", "done"),
        ("generate", "running"),
        ("generate", "done"),
        ("persist", "running"),
        ("persist", "done"),
    ]
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "Первый русский факт" not in rendered_logs
    assert all(record.generation_document_id == "doc-ru-1" for record in generation_events(caplog))


def test_orchestrator_logs_repair_step_when_initial_generation_fails_quality(caplog, tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload(question_count=1), "resp-1"),
            build_response(build_payload(question_count=2), "resp-2"),
        ]
    )
    orchestrator, document_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    with caplog.at_level(logging.INFO):
        result = orchestrator.generate("doc-ru-1", build_generation_request(question_count=2))

    assert result.prompt_version == "repair-v1"
    assert ("repair", "running") in event_pairs(caplog)
    assert ("repair", "done") in event_pairs(caplog)
    repair_events = [
        record
        for record in generation_events(caplog)
        if record.generation_step == "repair"
    ]
    assert repair_events[0].generation_metadata["attempt"] == 1
    assert repair_events[0].generation_metadata["initial_error_code"] == "generation_quality_error"


def test_orchestrator_logs_failed_step_when_generation_cannot_be_repaired(caplog, tmp_path) -> None:
    provider = StubProvider(
        [
            build_response(build_payload(question_count=1), "resp-1"),
            build_response(build_payload(question_count=1), "resp-2"),
        ]
    )
    orchestrator, document_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())

    with caplog.at_level(logging.INFO), pytest.raises(GenerationQualityError):
        orchestrator.generate("doc-ru-1", build_generation_request(question_count=2))

    assert ("repair", "failed") in event_pairs(caplog)
    failed_events = [
        record
        for record in generation_events(caplog)
        if record.generation_status == "failed"
    ]
    assert failed_events[-1].generation_error_code == "generation_quality_error"
