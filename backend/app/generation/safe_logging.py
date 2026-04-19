"""Helpers for redacted generation logging."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult


def summarize_document_payload(document: DocumentRecord) -> dict[str, Any]:
    """Return a redacted summary of a stored document payload."""

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "media_type": document.media_type,
        "file_size_bytes": document.file_size_bytes,
        "text_length": len(document.normalized_text),
        "text_digest": _digest_text(document.normalized_text),
    }


def summarize_generation_request(request: GenerationRequest) -> dict[str, Any]:
    """Return a redacted summary of a generation request."""

    return {
        "question_count": request.question_count,
        "language": request.language,
        "difficulty": request.difficulty,
        "quiz_type": request.quiz_type,
        "generation_mode": request.generation_mode.value,
    }


def summarize_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted summary of model-produced structured content."""

    serialized_payload = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return {
        "top_level_keys": sorted(payload.keys()),
        "payload_length": len(serialized_payload),
        "payload_digest": _digest_text(serialized_payload),
    }


def summarize_generation_result(result: GenerationResult) -> dict[str, Any]:
    """Return a redacted summary of a persisted generation result."""

    return {
        "quiz_id": result.quiz.quiz_id,
        "document_id": result.quiz.document_id,
        "question_count": len(result.quiz.questions),
        "model_name": result.model_name,
        "prompt_version": result.prompt_version,
    }


def _digest_text(value: str) -> str:
    """Build a short stable digest for sensitive text."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
