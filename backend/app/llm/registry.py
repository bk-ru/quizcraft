"""Typed provider registry and enablement enforcement."""

from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from backend.app.domain.errors import ProviderDisabledError
from backend.app.domain.errors import UnsupportedProviderError
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.llm.provider import LLMProvider


class ProviderName(str, Enum):
    """Supported provider identifiers."""

    LM_STUDIO = "lm_studio"
    OLLAMA = "ollama"
    EXTERNAL_API = "external_api"

    @classmethod
    def normalize(cls, provider_name: "ProviderName | str") -> "ProviderName":
        """Normalize a provider identifier into a typed enum value."""

        if isinstance(provider_name, cls):
            return provider_name
        if not isinstance(provider_name, str):
            raise ValueError("provider name must be a string")
        normalized_name = provider_name.strip().lower()
        for supported_provider in cls:
            if supported_provider.value == normalized_name:
                return supported_provider
        supported_message = ", ".join(provider.value for provider in cls)
        raise ValueError(
            f"provider '{provider_name}' is not supported; supported providers: {supported_message}"
        )


class ProviderRegistry:
    """Registry of configured providers with feature-flag enforcement."""

    def __init__(
        self,
        providers: Mapping[ProviderName | str, LLMProvider],
        enabled_providers: Iterable[ProviderName | str],
    ) -> None:
        normalized_providers: dict[ProviderName, LLMProvider] = {}
        for provider_name, provider in providers.items():
            normalized_provider_name = ProviderName.normalize(provider_name)
            if normalized_provider_name in normalized_providers:
                raise ValueError(f"provider '{normalized_provider_name.value}' is registered more than once")
            normalized_providers[normalized_provider_name] = provider
        self._providers = MappingProxyType(normalized_providers)
        self._enabled_providers = frozenset(ProviderName.normalize(provider) for provider in enabled_providers)

    @property
    def registered_provider_names(self) -> tuple[ProviderName, ...]:
        """Return registered provider names in deterministic order."""

        return tuple(provider for provider in ProviderName if provider in self._providers)

    @property
    def enabled_provider_names(self) -> tuple[ProviderName, ...]:
        """Return enabled provider names in deterministic order."""

        return tuple(provider for provider in ProviderName if provider in self._enabled_providers)

    def is_enabled(self, provider_name: ProviderName | str) -> bool:
        """Return whether a provider is enabled by feature flags."""

        return ProviderName.normalize(provider_name) in self._enabled_providers

    def ensure_enabled(self, provider_name: ProviderName | str) -> ProviderName:
        """Return the normalized provider name or raise if it is disabled."""

        normalized_provider_name = ProviderName.normalize(provider_name)
        if normalized_provider_name not in self._enabled_providers:
            raise ProviderDisabledError(normalized_provider_name.value)
        return normalized_provider_name

    def enforced_provider(self, provider_name: ProviderName | str) -> LLMProvider:
        """Return a provider wrapper that enforces provider feature flags."""

        normalized_provider_name = ProviderName.normalize(provider_name)
        provider = self._providers.get(normalized_provider_name)
        if provider is None:
            registered_names = tuple(provider.value for provider in self.registered_provider_names)
            raise UnsupportedProviderError(normalized_provider_name.value, registered_names)
        return RegistryEnforcedProvider(
            provider_name=normalized_provider_name,
            provider=provider,
            registry=self,
        )


@dataclass(frozen=True, slots=True)
class RegistryEnforcedProvider(LLMProvider):
    """Provider wrapper that blocks calls when its provider is disabled."""

    provider_name: ProviderName
    provider: LLMProvider
    registry: ProviderRegistry

    def healthcheck(self) -> ProviderHealthStatus:
        """Return provider health or a disabled status without calling the provider."""

        if not self.registry.is_enabled(self.provider_name):
            return ProviderHealthStatus(
                status="disabled",
                message=f"Provider '{self.provider_name.value}' is disabled by PROVIDERS_ENABLED",
            )
        return self.provider.healthcheck()

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Generate a structured payload when the provider is enabled."""

        self.registry.ensure_enabled(self.provider_name)
        return self.provider.generate_structured(request)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings when the provider is enabled."""

        self.registry.ensure_enabled(self.provider_name)
        return self.provider.embed(request)
