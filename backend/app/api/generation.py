"""Direct-generation endpoint for the HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request

from backend.app.api.runtime import get_generation_dispatcher
from backend.app.api.runtime import get_generation_settings_repository
from backend.app.api.schemas import GenerationRequestBody
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import GenerationSettings
from backend.app.generation.profiles import GenerationProfileResolver


def register_generation_routes(app: FastAPI) -> None:
    """Register generation routes on the FastAPI app."""

    @app.post("/documents/{document_id}/generate")
    async def generate_quiz(
        request: Request,
        document_id: str,
        payload: GenerationRequestBody,
    ) -> dict[str, Any]:
        settings_repository = get_generation_settings_repository(request.app)
        settings = payload.to_settings(defaults=_load_saved_settings(settings_repository))
        profile = GenerationProfileResolver(request.app.state.config).resolve(
            model_name=settings.model_name,
            profile_name=settings.profile_name,
        )
        result = get_generation_dispatcher(request.app).dispatch(
            document_id,
            settings.to_generation_request(
                model_name=profile.model_name,
                profile_name=profile.profile_name,
                inference_parameters=dict(profile.inference_parameters),
            ),
        )
        settings_repository.save(settings)
        return _serialize_generation_result(result, request.state.correlation_id)


def _load_saved_settings(settings_repository) -> GenerationSettings | None:
    """Load saved generation settings if they exist."""

    try:
        return settings_repository.get()
    except RepositoryNotFoundError:
        return None


def _serialize_generation_result(result: GenerationResult, request_id: str) -> dict[str, Any]:
    """Serialize a generation result for API responses."""

    return {
        "quiz_id": result.quiz.quiz_id,
        "quiz": result.quiz.to_dict(),
        "model_name": result.model_name,
        "prompt_version": result.prompt_version,
        "request_id": request_id,
    }
