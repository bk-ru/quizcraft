"""Filesystem-backed diagnostic artifacts for generation debugging."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation.safe_logging import summarize_document_payload
from backend.app.generation.safe_logging import summarize_generation_request
from backend.app.generation.safe_logging import summarize_model_payload


class FileSystemGenerationDiagnosticLogger:
    """Persist generation diagnostics for local debugging without storing full documents."""

    def __init__(self, root_path: Path, document_preview_chars: int = 500) -> None:
        if document_preview_chars < 0:
            raise ValueError("document_preview_chars must be zero or greater")
        self._storage_path = Path(root_path) / "generation_logs"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._document_preview_chars = document_preview_chars

    @property
    def storage_path(self) -> Path:
        """Return the directory containing diagnostic JSON artifacts."""

        return self._storage_path

    def log_success(
        self,
        *,
        pipeline: str,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        prompt_version: str,
        provider_request: dict[str, Any],
        response: StructuredGenerationResponse,
        quiz: Quiz,
        rag_metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Persist a compact successful generation diagnostic artifact."""

        return self._write_record(
            status="success",
            pipeline=pipeline,
            document=document,
            generation_request=generation_request,
            prompt_version=prompt_version,
            provider_request=provider_request,
            response=response,
            quiz=quiz,
            rag_metadata=rag_metadata,
            include_raw_model_content=False,
        )

    def log_validation_failure(
        self,
        *,
        pipeline: str,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        prompt_version: str,
        provider_request: dict[str, Any],
        response: StructuredGenerationResponse,
        error: Exception,
        quiz: Quiz | None = None,
        rag_metadata: dict[str, Any] | None = None,
        repair_attempt: int | None = None,
    ) -> Path:
        """Persist a validation failure with raw model content for root-cause analysis."""

        return self._write_record(
            status="validation_failed",
            pipeline=pipeline,
            document=document,
            generation_request=generation_request,
            prompt_version=prompt_version,
            provider_request=provider_request,
            response=response,
            quiz=quiz,
            rag_metadata=rag_metadata,
            error=error,
            repair_attempt=repair_attempt,
            include_raw_model_content=True,
        )

    def log_runtime_failure(
        self,
        *,
        pipeline: str,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        stage: str,
        error: Exception,
        rag_metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Persist a non-validation failure such as provider, embedding, or persistence errors."""

        now = datetime.now(UTC)
        record: dict[str, Any] = {
            "run_id": f"run-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "status": "runtime_failed",
            "pipeline": pipeline,
            "stage": stage,
            "document": self._document_payload(document),
            "generation_request": summarize_generation_request(generation_request),
            "generation_request_raw": generation_request.to_dict(),
            "error": {
                "type": error.__class__.__name__,
                "code": getattr(error, "code", error.__class__.__name__),
                "message": str(getattr(error, "message", str(error))),
            },
        }
        if rag_metadata is not None:
            record["rag"] = dict(rag_metadata)

        target_path = self._storage_path / f"{record['run_id']}.json"
        target_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return target_path

    def _write_record(
        self,
        *,
        status: str,
        pipeline: str,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        prompt_version: str,
        provider_request: dict[str, Any],
        response: StructuredGenerationResponse,
        quiz: Quiz | None,
        include_raw_model_content: bool,
        rag_metadata: dict[str, Any] | None = None,
        error: Exception | None = None,
        repair_attempt: int | None = None,
    ) -> Path:
        now = datetime.now(UTC)
        record: dict[str, Any] = {
            "run_id": f"run-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "status": status,
            "pipeline": pipeline,
            "document": self._document_payload(document),
            "generation_request": summarize_generation_request(generation_request),
            "generation_request_raw": generation_request.to_dict(),
            "prompt_version": prompt_version,
            "provider_request": provider_request,
            "provider_response": self._response_payload(
                response,
                include_raw_model_content=include_raw_model_content,
            ),
            "quiz_summary": None if quiz is None else self._quiz_payload(quiz),
        }
        if rag_metadata is not None:
            record["rag"] = dict(rag_metadata)
        if repair_attempt is not None:
            record["repair_attempt"] = repair_attempt
        if error is not None:
            record["error"] = {
                "type": error.__class__.__name__,
                "code": getattr(error, "code", error.__class__.__name__),
                "message": str(getattr(error, "message", str(error))),
            }

        target_path = self._storage_path / f"{record['run_id']}.json"
        target_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return target_path

    def _document_payload(self, document: DocumentRecord) -> dict[str, Any]:
        payload = summarize_document_payload(document)
        if self._document_preview_chars:
            payload["text_preview"] = document.normalized_text[: self._document_preview_chars]
        return payload

    @staticmethod
    def _response_payload(
        response: StructuredGenerationResponse,
        *,
        include_raw_model_content: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model_name": response.model_name,
            "content_summary": summarize_model_payload(response.content),
            "raw_response_keys": sorted(response.raw_response) if isinstance(response.raw_response, dict) else [],
        }
        if include_raw_model_content:
            payload["raw_model_content"] = response.content
        return payload

    @staticmethod
    def _quiz_payload(quiz: Quiz) -> dict[str, Any]:
        return {
            "quiz_id": quiz.quiz_id,
            "document_id": quiz.document_id,
            "title": quiz.title,
            "question_count": len(quiz.questions),
            "question_types": [question.question_type for question in quiz.questions],
            "option_counts": [len(question.options) for question in quiz.questions],
            "matching_pair_counts": [len(question.matching_pairs) for question in quiz.questions],
        }


def summarize_structured_generation_request(request: StructuredGenerationRequest) -> dict[str, Any]:
    """Return a prompt-safe summary of the outbound provider request."""

    return {
        "model_name": request.model_name,
        "schema_name": request.schema_name,
        "schema_top_level_keys": sorted(request.schema),
        "system_prompt_chars": len(request.system_prompt),
        "user_prompt_chars": len(request.user_prompt),
        "user_prompt_preview": request.user_prompt[:500],
        "inference_parameters": dict(request.inference_parameters),
    }
