"""Direct-generation endpoint for the HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request

from backend.app.api.runtime import get_generation_orchestrator
from backend.app.core.modes import GenerationModeRegistry
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult


def register_generation_routes(app: FastAPI) -> None:
    """Register generation routes on the FastAPI app."""

    @app.post("/documents/{document_id}/generate")
    async def generate_quiz(request: Request, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        generation_request = _build_generation_request(payload)
        result = get_generation_orchestrator(request.app).generate(document_id, generation_request)
        return _serialize_generation_result(result, request.state.correlation_id)


def _build_generation_request(payload: dict[str, Any]) -> GenerationRequest:
    """Build a validated generation request from a raw JSON payload."""

    return GenerationRequest(
        question_count=_require_positive_int(payload, "question_count"),
        language=_require_non_empty_string(payload, "language"),
        difficulty=_require_non_empty_string(payload, "difficulty"),
        quiz_type=_require_non_empty_string(payload, "quiz_type"),
        generation_mode=GenerationModeRegistry.ensure_supported(
            _require_non_empty_string(payload, "generation_mode")
        ),
    )


def _require_non_empty_string(payload: dict[str, Any], field_name: str) -> str:
    """Require a non-empty string field from a JSON payload."""

    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_positive_int(payload: dict[str, Any], field_name: str) -> int:
    """Require a positive integer field from a JSON payload."""

    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DomainValidationError(f"{field_name} must be a positive integer")
    return value


def _serialize_generation_result(result: GenerationResult, request_id: str) -> dict[str, Any]:
    """Serialize a generation result for API responses."""

    return {
        "quiz_id": result.quiz.quiz_id,
        "quiz": result.quiz.to_dict(),
        "model_name": result.model_name,
        "prompt_version": result.prompt_version,
        "request_id": request_id,
    }
