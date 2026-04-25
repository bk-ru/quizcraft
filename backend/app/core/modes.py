"""Generation mode registry."""

from __future__ import annotations

from enum import Enum

from backend.app.domain.errors import UnsupportedGenerationModeError


class GenerationMode(str, Enum):
    """Supported generation modes for the backend."""

    DIRECT = "direct"
    SINGLE_QUESTION_REGEN = "single_question_regen"
    RAG = "rag"


class GenerationModeRegistry:
    """Registry for supported generation modes."""

    _registry = {mode.value: mode for mode in GenerationMode}

    @classmethod
    def ensure_supported(cls, mode_name: str) -> GenerationMode:
        """Return a supported generation mode or raise a domain error."""

        normalized_mode = mode_name.strip().lower()
        try:
            return cls._registry[normalized_mode]
        except KeyError as error:
            raise UnsupportedGenerationModeError(f"unsupported generation mode: {mode_name}") from error
