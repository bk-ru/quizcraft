from __future__ import annotations

import pytest

from backend.app.core.config import AppConfig
from backend.app.domain.errors import ProviderDisabledError
from backend.app.domain.models import ProviderHealthStatus
from backend.app.llm.factory import build_provider_runtime
from backend.app.llm.ollama import OllamaClient
from backend.app.llm.registry import ProviderName


class StubProvider:
    """Provider test double for provider factory tests."""

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="stub available")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by provider factory tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by provider factory tests")


def build_lm_studio_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
    )


def build_ollama_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:7b",
        ollama_embedding_model="nomic-embed-text",
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.OLLAMA,
        log_format="%(levelname)s:%(message)s",
    )


def test_build_provider_runtime_preserves_injected_lm_studio_provider() -> None:
    provider = StubProvider()

    runtime = build_provider_runtime(build_lm_studio_config(), provider=provider)

    assert runtime.registry.registered_provider_names == (ProviderName.LM_STUDIO,)
    assert runtime.active_provider.healthcheck().status == "available"


def test_build_provider_runtime_registers_ollama_as_active_provider_without_lm_studio_initialization() -> None:
    runtime = build_provider_runtime(build_ollama_config())

    assert runtime.registry.registered_provider_names == (ProviderName.OLLAMA,)
    assert isinstance(runtime.active_provider.provider, OllamaClient)


def test_build_provider_runtime_wraps_disabled_default_provider() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        ollama_model="qwen2.5:7b",
        allowed_models=("local-model", "qwen2.5:7b"),
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.LM_STUDIO,
        log_format="%(levelname)s:%(message)s",
    )
    runtime = build_provider_runtime(config, provider=StubProvider())

    with pytest.raises(ProviderDisabledError, match="lm_studio"):
        runtime.active_provider.embed(request=None)
