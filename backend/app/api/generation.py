"""Direct-generation endpoint for the HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request

from backend.app.api.runtime import get_generation_orchestrator
from backend.app.api.schemas import GenerationRequestBody
from backend.app.domain.models import GenerationResult


def register_generation_routes(app: FastAPI) -> None:
    """Register generation routes on the FastAPI app."""

    @app.post("/documents/{document_id}/generate")
    async def generate_quiz(
        request: Request,
        document_id: str,
        payload: GenerationRequestBody,
    ) -> dict[str, Any]:
        result = get_generation_orchestrator(request.app).generate(document_id, payload.to_domain())
        return _serialize_generation_result(result, request.state.correlation_id)


def _serialize_generation_result(result: GenerationResult, request_id: str) -> dict[str, Any]:
    """Serialize a generation result for API responses."""

    return {
        "quiz_id": result.quiz.quiz_id,
        "quiz": result.quiz.to_dict(),
        "model_name": result.model_name,
        "prompt_version": result.prompt_version,
        "request_id": request_id,
    }
