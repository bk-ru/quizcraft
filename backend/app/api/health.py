"""Health endpoints for the backend API surface."""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.core.config import AppConfig
from backend.app.core.modes import GenerationMode
from backend.app.llm.registry import ProviderName


def register_health_routes(app: FastAPI, config: AppConfig) -> None:
    """Register backend and provider health endpoints on the app."""

    @app.get("/health")
    async def backend_health() -> dict[str, object]:
        return {
            "status": "ok",
            "default_model": config.default_model,
            "generation_modes": [mode.value for mode in GenerationMode],
            "providers_enabled": [provider.value for provider in config.providers_enabled],
        }

    @app.get("/health/lm-studio")
    async def lm_studio_health() -> dict[str, str]:
        if ProviderName.LM_STUDIO not in config.providers_enabled:
            return {
                "status": "disabled",
                "message": "Provider 'lm_studio' is disabled by PROVIDERS_ENABLED",
                "default_model": config.lm_studio_model,
            }
        health = app.state.provider_registry.enforced_provider(ProviderName.LM_STUDIO).healthcheck()
        return {
            "status": health.status,
            "message": health.message,
            "default_model": config.lm_studio_model,
        }

    @app.get("/health/ollama")
    async def ollama_health() -> dict[str, str]:
        default_model = config.ollama_model or config.lm_studio_model
        embedding_model = config.ollama_embedding_model or default_model
        if ProviderName.OLLAMA not in config.providers_enabled:
            return {
                "status": "disabled",
                "message": "Provider 'ollama' is disabled by PROVIDERS_ENABLED",
                "default_model": default_model,
                "embedding_model": embedding_model,
            }
        health = app.state.provider_registry.enforced_provider(ProviderName.OLLAMA).healthcheck()
        return {
            "status": health.status,
            "message": health.message,
            "default_model": default_model,
            "embedding_model": embedding_model,
        }
