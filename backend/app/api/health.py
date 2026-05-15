"""Endpoint'ы проверки состояния для поверхности backend API."""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi import Request

from backend.app.api.schemas import LMStudioConnectionBody
from backend.app.core.config import AppConfig
from backend.app.core.modes import GenerationMode
from backend.app.llm.factory import build_provider_runtime
from backend.app.llm.registry import ProviderName


def register_health_routes(app: FastAPI, config: AppConfig) -> None:
    """Зарегистрировать endpoint'ы состояния backend и провайдера в приложении."""

    @app.get("/health")
    async def backend_health() -> dict[str, object]:
        current_config = app.state.config
        return {
            "status": "ok",
            "default_provider": current_config.default_provider.value,
            "default_model": current_config.default_model,
            "generation_modes": [mode.value for mode in GenerationMode],
            "providers_enabled": [provider.value for provider in current_config.providers_enabled],
        }

    @app.get("/health/provider")
    async def default_provider_health() -> dict[str, object]:
        current_config = app.state.config
        provider_name = current_config.default_provider
        health = app.state.provider_registry.enforced_provider(provider_name).healthcheck()
        return {
            "provider": provider_name.value,
            "status": health.status,
            "message": health.message,
            "default_model": current_config.default_model,
            "embedding_model": current_config.default_embedding_model,
            "available_models": list(health.available_models),
        }

    @app.get("/providers/lm-studio/connection")
    async def get_lm_studio_connection(request: Request) -> dict[str, object]:
        return _serialize_lm_studio_connection(request.app)

    @app.put("/providers/lm-studio/connection")
    async def update_lm_studio_connection(
        request: Request,
        payload: LMStudioConnectionBody,
    ) -> dict[str, object]:
        updated_config = replace(request.app.state.config, lm_studio_base_url=payload.to_base_url())
        provider_runtime = build_provider_runtime(updated_config)
        request.app.state.config = updated_config
        request.app.state.provider_registry = provider_runtime.registry
        request.app.state.provider = provider_runtime.active_provider
        _invalidate_generation_runtime(request.app)
        return _serialize_lm_studio_connection(request.app)

    @app.get("/health/lm-studio")
    async def lm_studio_health() -> dict[str, object]:
        current_config = app.state.config
        if ProviderName.LM_STUDIO not in current_config.providers_enabled:
            return {
                "status": "disabled",
                "message": "Provider 'lm_studio' is disabled by PROVIDERS_ENABLED",
                "default_model": current_config.lm_studio_model,
                "available_models": [],
            }
        health = app.state.provider_registry.enforced_provider(ProviderName.LM_STUDIO).healthcheck()
        return {
            "status": health.status,
            "message": health.message,
            "default_model": current_config.lm_studio_model,
            "available_models": list(health.available_models),
        }

    @app.get("/health/ollama")
    async def ollama_health() -> dict[str, object]:
        current_config = app.state.config
        default_model = current_config.ollama_model or current_config.lm_studio_model
        embedding_model = current_config.ollama_embedding_model or default_model
        if ProviderName.OLLAMA not in current_config.providers_enabled:
            return {
                "status": "disabled",
                "message": "Provider 'ollama' is disabled by PROVIDERS_ENABLED",
                "default_model": default_model,
                "embedding_model": embedding_model,
                "available_models": [],
            }
        health = app.state.provider_registry.enforced_provider(ProviderName.OLLAMA).healthcheck()
        return {
            "status": health.status,
            "message": health.message,
            "default_model": default_model,
            "embedding_model": embedding_model,
            "available_models": list(health.available_models),
        }

    @app.get("/health/external-api")
    async def external_api_health() -> dict[str, object]:
        current_config = app.state.config
        default_model = current_config.external_api_model or current_config.lm_studio_model
        embedding_model = current_config.external_api_embedding_model or default_model
        if ProviderName.EXTERNAL_API not in current_config.providers_enabled:
            return {
                "status": "disabled",
                "message": "Provider 'external_api' is disabled by PROVIDERS_ENABLED",
                "default_model": default_model,
                "embedding_model": embedding_model,
                "available_models": [],
            }
        health = app.state.provider_registry.enforced_provider(ProviderName.EXTERNAL_API).healthcheck()
        return {
            "status": health.status,
            "message": health.message,
            "default_model": default_model,
            "embedding_model": embedding_model,
            "available_models": list(health.available_models),
        }


def _serialize_lm_studio_connection(app: FastAPI) -> dict[str, object]:
    config: AppConfig = app.state.config
    host, port = _parse_lm_studio_host_port(config.lm_studio_base_url)
    if ProviderName.LM_STUDIO not in config.providers_enabled:
        return {
            "provider": ProviderName.LM_STUDIO.value,
            "host": host,
            "port": port,
            "base_url": config.lm_studio_base_url,
            "status": "disabled",
            "message": "Provider 'lm_studio' is disabled by PROVIDERS_ENABLED",
            "default_model": config.lm_studio_model,
            "embedding_model": config.lm_studio_embedding_model or config.lm_studio_model,
        }
    health = app.state.provider_registry.enforced_provider(ProviderName.LM_STUDIO).healthcheck()
    return {
        "provider": ProviderName.LM_STUDIO.value,
        "host": host,
        "port": port,
        "base_url": config.lm_studio_base_url,
        "status": health.status,
        "message": health.message,
        "default_model": config.lm_studio_model,
        "embedding_model": config.lm_studio_embedding_model or config.lm_studio_model,
        "available_models": list(health.available_models),
    }


def _parse_lm_studio_host_port(base_url: str) -> tuple[str, int]:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return host, port


def _invalidate_generation_runtime(app: FastAPI) -> None:
    for attribute_name in (
        "generation_orchestrator",
        "rag_generation_orchestrator",
        "generation_dispatcher",
        "single_question_regeneration_orchestrator",
    ):
        if hasattr(app.state, attribute_name):
            delattr(app.state, attribute_name)
