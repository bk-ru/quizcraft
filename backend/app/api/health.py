"""Health endpoints for the backend API surface."""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.core.config import AppConfig
from backend.app.core.modes import GenerationMode


def register_health_routes(app: FastAPI, config: AppConfig) -> None:
    """Register backend and LM Studio health endpoints on the app."""

    @app.get("/health")
    async def backend_health() -> dict[str, object]:
        return {
            "status": "ok",
            "default_model": config.lm_studio_model,
            "generation_modes": [mode.value for mode in GenerationMode],
            "providers_enabled": [provider.value for provider in config.providers_enabled],
        }

    @app.get("/health/lm-studio")
    async def lm_studio_health() -> dict[str, str]:
        health = app.state.provider.healthcheck()
        return {
            "status": health.status,
            "message": health.message,
            "default_model": config.lm_studio_model,
        }
