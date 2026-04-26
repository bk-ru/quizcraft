from __future__ import annotations

import pytest

from backend.app.domain.errors import ProviderDisabledError
from backend.app.domain.errors import UnsupportedProviderError
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.llm.registry import ProviderName
from backend.app.llm.registry import ProviderRegistry


class StubProvider:
    """Provider test double for provider registry enforcement tests."""

    def __init__(self) -> None:
        self.healthcheck_calls = 0
        self.generate_calls = 0
        self.embed_calls = 0

    def healthcheck(self) -> ProviderHealthStatus:
        self.healthcheck_calls += 1
        return ProviderHealthStatus(status="available", message="LM Studio доступен")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.generate_calls += 1
        return StructuredGenerationResponse(
            model_name="local-model",
            content={"title": "Русский квиз"},
            raw_response={"id": "resp-1"},
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.embed_calls += 1
        return EmbeddingResponse(model_name="local-model", vectors=((1.0, 0.0),))


def build_structured_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        system_prompt="Сформируй квиз.",
        user_prompt="Документ: Москва — столица России.",
        schema_name="quiz_payload",
        schema={"type": "object"},
    )


def test_provider_name_normalizes_supported_values() -> None:
    assert ProviderName.normalize(" LM_STUDIO ") is ProviderName.LM_STUDIO
    assert ProviderName.normalize("ollama") is ProviderName.OLLAMA
    assert ProviderName.normalize(ProviderName.EXTERNAL_API) is ProviderName.EXTERNAL_API


def test_provider_name_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="not supported"):
        ProviderName.normalize("unknown")


def test_registry_forwards_calls_for_enabled_provider() -> None:
    provider = StubProvider()
    registry = ProviderRegistry(
        providers={ProviderName.LM_STUDIO: provider},
        enabled_providers=(ProviderName.LM_STUDIO,),
    )
    enforced_provider = registry.enforced_provider("lm_studio")

    health = enforced_provider.healthcheck()
    structured_response = enforced_provider.generate_structured(build_structured_request())
    embedding_response = enforced_provider.embed(EmbeddingRequest(texts=("Москва",)))

    assert health.status == "available"
    assert structured_response.content["title"] == "Русский квиз"
    assert embedding_response.vectors == ((1.0, 0.0),)
    assert provider.healthcheck_calls == 1
    assert provider.generate_calls == 1
    assert provider.embed_calls == 1


def test_registry_blocks_generation_and_embeddings_for_disabled_provider() -> None:
    provider = StubProvider()
    registry = ProviderRegistry(
        providers={ProviderName.LM_STUDIO: provider},
        enabled_providers=(ProviderName.OLLAMA,),
    )
    enforced_provider = registry.enforced_provider(ProviderName.LM_STUDIO)

    health = enforced_provider.healthcheck()
    with pytest.raises(ProviderDisabledError, match="lm_studio"):
        enforced_provider.generate_structured(build_structured_request())
    with pytest.raises(ProviderDisabledError, match="lm_studio"):
        enforced_provider.embed(EmbeddingRequest(texts=("Москва",)))

    assert health.status == "disabled"
    assert provider.healthcheck_calls == 0
    assert provider.generate_calls == 0
    assert provider.embed_calls == 0


def test_registry_rejects_unregistered_provider() -> None:
    registry = ProviderRegistry(
        providers={ProviderName.LM_STUDIO: StubProvider()},
        enabled_providers=(ProviderName.LM_STUDIO,),
    )

    with pytest.raises(UnsupportedProviderError, match="ollama"):
        registry.enforced_provider(ProviderName.OLLAMA)
