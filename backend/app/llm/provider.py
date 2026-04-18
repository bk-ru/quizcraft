"""Provider contract for model-backed generation services."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse


class LLMProvider(ABC):
    """Abstract provider boundary for model generation capabilities."""

    @abstractmethod
    def healthcheck(self) -> ProviderHealthStatus:
        """Return provider availability information."""

    @abstractmethod
    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Generate a structured JSON payload for the given prompts and schema."""

    @abstractmethod
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings for one or more texts."""
