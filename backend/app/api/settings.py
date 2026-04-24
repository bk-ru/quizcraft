"""Generation settings endpoints for the HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request

from backend.app.api.runtime import get_generation_settings_repository
from backend.app.api.schemas import GenerationSettingsBody
from backend.app.core.config import AppConfig
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationSettings
from backend.app.generation.profiles import GenerationProfileResolver


def register_generation_settings_routes(app: FastAPI) -> None:
    """Register generation settings routes on the FastAPI app."""

    @app.get("/generation/settings")
    async def get_generation_settings(request: Request) -> dict[str, Any]:
        try:
            settings: GenerationSettings | None = get_generation_settings_repository(request.app).get()
        except RepositoryNotFoundError:
            settings = None
        return _serialize_generation_settings(
            settings,
            request.state.correlation_id,
            request.app.state.config,
        )

    @app.put("/generation/settings")
    async def save_generation_settings(
        request: Request,
        payload: GenerationSettingsBody,
    ) -> dict[str, Any]:
        settings = payload.to_settings()
        GenerationProfileResolver(request.app.state.config).resolve(
            model_name=settings.model_name,
            profile_name=settings.profile_name,
        )
        saved = get_generation_settings_repository(request.app).save(settings)
        return _serialize_generation_settings(
            saved,
            request.state.correlation_id,
            request.app.state.config,
        )


def _serialize_generation_settings(
    settings: GenerationSettings | None,
    request_id: str,
    config: AppConfig,
) -> dict[str, Any]:
    """Serialize generation settings for API responses."""

    return {
        "settings": None if settings is None else settings.to_dict(),
        "available_models": list(config.allowed_models),
        "default_model": config.lm_studio_model,
        "available_profiles": list(config.generation_profiles.keys()),
        "default_profile": config.default_generation_profile,
        "request_id": request_id,
    }
