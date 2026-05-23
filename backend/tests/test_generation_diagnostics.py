from __future__ import annotations

import json

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import LLMRequestError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.diagnostics import FileSystemGenerationDiagnosticLogger
from backend.app.generation.diagnostics import summarize_structured_generation_request


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-diagnostic",
        filename="лекция.txt",
        media_type="text/plain",
        file_size_bytes=2048,
        normalized_text="Русский диагностический текст. " * 80,
        metadata={"text_length": 2400},
    )


def build_request() -> GenerationRequest:
    return GenerationRequest(
        question_count=5,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.RAG,
        quiz_types=("single_choice",),
    )


def build_response() -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name="google/gemma-4-e2b",
        content={
            "quiz_id": "quiz-diagnostic",
            "document_id": "doc-diagnostic",
            "title": "Диагностика",
            "questions": [
                {
                    "question_id": "q1",
                    "question_type": "matching",
                    "prompt": "Сопоставьте понятия",
                    "matching_pairs": [
                        {"left": "TXT", "right": "Текстовый файл"},
                        {"left": "PDF", "right": "Документ"},
                    ],
                }
            ],
        },
        raw_response={"id": "resp-1", "choices": []},
    )


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-diagnostic",
        document_id="doc-diagnostic",
        title="Диагностика",
        version=1,
        last_edited_at="2026-05-05T12:00:00Z",
        questions=(
            Question(
                question_id="q1",
                question_type="matching",
                prompt="Сопоставьте понятия",
                matching_pairs=(
                    MatchingPair(left="TXT", right="Текстовый файл"),
                    MatchingPair(left="PDF", right="Документ"),
                ),
            ),
        ),
    )


def test_diagnostic_logger_persists_validation_failure_with_raw_model_content(tmp_path) -> None:
    logger = FileSystemGenerationDiagnosticLogger(tmp_path, document_preview_chars=32)
    response = build_response()

    path = logger.log_validation_failure(
        pipeline="rag",
        document=build_document(),
        generation_request=build_request(),
        prompt_version="rag-v1",
        provider_request={"model_name": "google/gemma-4-e2b", "user_prompt_chars": 1200},
        response=response,
        quiz=build_quiz(),
        error=DomainValidationError("matching question must have at least four pairs"),
        rag_metadata={"chunk_count": 17, "retrieved_chunks": 8},
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "validation_failed"
    assert payload["pipeline"] == "rag"
    assert payload["generation_request_raw"]["quiz_types"] == ["single_choice"]
    assert payload["provider_response"]["raw_model_content"] == response.content
    assert payload["provider_request"]["prompt_version"] == "rag-v1"
    assert payload["quiz_summary"]["question_types"] == ["matching"]
    assert payload["quiz_summary"]["matching_pair_counts"] == [2]
    assert payload["rag"]["chunk_count"] == 17
    assert payload["error"]["message"] == "matching question must have at least four pairs"
    assert payload["document"]["text_preview"] == build_document().normalized_text[:32]
    assert len(payload["document"]["text_preview"]) < len(build_document().normalized_text)


def test_diagnostic_logger_omits_raw_model_content_on_success(tmp_path) -> None:
    logger = FileSystemGenerationDiagnosticLogger(tmp_path)

    path = logger.log_success(
        pipeline="direct",
        document=build_document(),
        generation_request=build_request(),
        prompt_version="direct-v1",
        provider_request={"model_name": "google/gemma-4-e2b"},
        response=build_response(),
        quiz=build_quiz(),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert "raw_model_content" not in payload["provider_response"]


def test_diagnostic_logger_persists_runtime_failures(tmp_path) -> None:
    logger = FileSystemGenerationDiagnosticLogger(tmp_path)

    path = logger.log_runtime_failure(
        pipeline="rag",
        document=build_document(),
        generation_request=build_request(),
        stage="generate",
        error=RuntimeError("LM Studio returned request error 400"),
        rag_metadata={"chunk_count": 17},
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "runtime_failed"
    assert payload["stage"] == "generate"
    assert payload["error"]["message"] == "LM Studio returned request error 400"
    assert payload["rag"]["chunk_count"] == 17


def test_diagnostic_logger_persists_error_diagnostics(tmp_path) -> None:
    logger = FileSystemGenerationDiagnosticLogger(tmp_path)
    error = LLMResponseFormatError(
        "LM Studio returned a malformed structured response",
        diagnostic={
            "reason": "message_content_invalid_json",
            "content_preview": "не-json",
            "response_keys": ["choices", "model"],
        },
    )

    path = logger.log_runtime_failure(
        pipeline="direct",
        document=build_document(),
        generation_request=build_request(),
        stage="generate",
        error=error,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["error"]["diagnostic"] == {
        "reason": "message_content_invalid_json",
        "content_preview": "не-json",
        "response_keys": ["choices", "model"],
    }


def test_diagnostic_logger_strips_prompt_previews_from_error_diagnostics(tmp_path) -> None:
    logger = FileSystemGenerationDiagnosticLogger(tmp_path)
    error = LLMRequestError(
        400,
        "LM Studio returned request error 400",
        diagnostic={
            "path": "/chat/completions",
            "request": {
                "message_count": 2,
                "user_prompt_preview": "Секретный русский текст документа",
                "first_input_preview": "Фрагмент документа",
                "message_chars": [12, 34],
            },
        },
    )

    path = logger.log_runtime_failure(
        pipeline="direct",
        document=build_document(),
        generation_request=build_request(),
        stage="generate",
        error=error,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    diagnostic = payload["error"]["diagnostic"]
    assert diagnostic["path"] == "/chat/completions"
    assert diagnostic["request"] == {"message_count": 2, "message_chars": [12, 34]}
    assert "Секретный русский текст документа" not in json.dumps(payload, ensure_ascii=False)
    assert "Фрагмент документа" not in json.dumps(payload, ensure_ascii=False)


def test_structured_request_summary_uses_lengths_and_preview(monkeypatch) -> None:
    monkeypatch.delenv("GENERATION_DIAGNOSTICS_INCLUDE_PROMPT", raising=False)
    request = StructuredGenerationRequest(
        system_prompt="system",
        user_prompt="Создай вопросы по документу. " * 40,
        schema_name="quiz_payload",
        schema={"type": "object", "properties": {}},
        inference_parameters={"temperature": 0.2},
        model_name="google/gemma-4-e2b",
    )

    summary = summarize_structured_generation_request(request)

    assert summary["model_name"] == "google/gemma-4-e2b"
    assert summary["schema_name"] == "quiz_payload"
    assert summary["user_prompt_chars"] == len(request.user_prompt)
    assert summary["user_prompt_preview"] == request.user_prompt[:500]
    assert summary["inference_parameters"] == {"temperature": 0.2}
    assert summary["schema_summary"] == {
        "top_level_keys": ["properties", "type"],
        "property_names": [],
        "required": [],
    }
    assert "system_prompt" not in summary
    assert "user_prompt" not in summary
    assert "schema" not in summary


def test_structured_request_summary_includes_full_prompt_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("GENERATION_DIAGNOSTICS_INCLUDE_PROMPT", "true")
    request = StructuredGenerationRequest(
        system_prompt="Системная инструкция",
        user_prompt="Создай вопросы по русскому документу.",
        schema_name="quiz_payload",
        schema={
            "type": "object",
            "required": ["questions"],
            "properties": {"questions": {"type": "array"}},
        },
        inference_parameters={"temperature": 0.2},
        model_name="google/gemma-4-e2b",
    )

    summary = summarize_structured_generation_request(request)

    assert summary["model_name"] == "google/gemma-4-e2b"
    assert summary["schema_name"] == "quiz_payload"
    assert summary["inference_parameters"] == {"temperature": 0.2}
    assert summary["system_prompt"] == request.system_prompt
    assert summary["user_prompt"] == request.user_prompt
    assert summary["schema"] == request.schema
