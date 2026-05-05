"""Registry режимов генерации."""

from __future__ import annotations

from enum import Enum

from backend.app.domain.errors import UnsupportedGenerationModeError


class GenerationMode(str, Enum):
    """Поддерживаемые режимы генерации для backend."""

    DIRECT = "direct"
    SINGLE_QUESTION_REGEN = "single_question_regen"
    RAG = "rag"


class GenerationModeRegistry:
    """Registry поддерживаемых режимов генерации."""

    _registry = {mode.value: mode for mode in GenerationMode}

    @classmethod
    def ensure_supported(cls, mode_name: str) -> GenerationMode:
        """Вернуть поддерживаемый режим генерации или вызвать доменную ошибку."""

        normalized_mode = mode_name.strip().lower()
        try:
            return cls._registry[normalized_mode]
        except KeyError as error:
            raise UnsupportedGenerationModeError(f"unsupported generation mode: {mode_name}") from error
