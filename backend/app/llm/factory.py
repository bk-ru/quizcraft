"""Provider registry construction for runtime wiring."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import AppConfig
from backend.app.llm.lm_studio import LMStudioClient
from backend.app.llm.ollama import OllamaClient
from backend.app.llm.provider import LLMProvider
from backend.app.llm.registry import ProviderName
from backend.app.llm.registry import ProviderRegistry


@dataclass(frozen=True, slots=True)
class ProviderRuntime:
    """Runtime provider graph resolved from application configuration."""

    registry: ProviderRegistry
    active_provider: LLMProvider


def build_provider_runtime(
    config: AppConfig,
    provider: LLMProvider | None = None,
) -> ProviderRuntime:
    """Build the provider registry and active provider for the application."""

    providers: dict[ProviderName, LLMProvider] = {}
    should_register_lm_studio = (
        provider is not None
        or ProviderName.LM_STUDIO in config.providers_enabled
        or config.default_provider is ProviderName.LM_STUDIO
    )
    if should_register_lm_studio:
        providers[ProviderName.LM_STUDIO] = provider or LMStudioClient(
            base_url=config.lm_studio_base_url,
            default_model=config.lm_studio_model,
            timeout_seconds=config.request_timeout,
        )
    should_register_ollama = (
        ProviderName.OLLAMA in config.providers_enabled
        or config.default_provider is ProviderName.OLLAMA
    )
    if should_register_ollama:
        providers[ProviderName.OLLAMA] = OllamaClient(
            base_url=config.ollama_base_url,
            default_model=config.ollama_model or config.lm_studio_model,
            default_embedding_model=config.ollama_embedding_model or config.ollama_model or config.lm_studio_model,
            timeout_seconds=config.request_timeout,
        )

    registry = ProviderRegistry(
        providers=providers,
        enabled_providers=config.providers_enabled,
    )
    return ProviderRuntime(
        registry=registry,
        active_provider=registry.enforced_provider(config.default_provider),
    )
