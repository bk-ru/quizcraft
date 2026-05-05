"""Контракт провайдера для сервисов генерации на основе моделей."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse


class LLMProvider(ABC):
    """Абстрактная граница провайдера для возможностей генерации модели."""

    @abstractmethod
    def healthcheck(self) -> ProviderHealthStatus:
        """Вернуть информацию о доступности провайдера."""

    @abstractmethod
    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Сгенерировать структурированный JSON payload для заданных prompts и schema."""

    @abstractmethod
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Сгенерировать embeddings для одного или нескольких текстов."""
