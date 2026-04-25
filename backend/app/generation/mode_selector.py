"""Rule-based selector for choosing between direct and RAG generation modes."""

from __future__ import annotations

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DomainValidationError

DEFAULT_RAG_THRESHOLD_CHARS = 6000


def select_generation_mode(
    *,
    requested_mode: GenerationMode,
    document_length_chars: int,
    rag_threshold_chars: int = DEFAULT_RAG_THRESHOLD_CHARS,
) -> GenerationMode:
    """Pick the effective generation mode for a request based on document size."""

    _validate_selector_inputs(
        requested_mode=requested_mode,
        document_length_chars=document_length_chars,
        rag_threshold_chars=rag_threshold_chars,
    )

    if requested_mode is GenerationMode.SINGLE_QUESTION_REGEN:
        return GenerationMode.SINGLE_QUESTION_REGEN
    if requested_mode is GenerationMode.RAG:
        return GenerationMode.RAG
    if document_length_chars > rag_threshold_chars:
        return GenerationMode.RAG
    return GenerationMode.DIRECT


def _validate_selector_inputs(
    *,
    requested_mode: GenerationMode,
    document_length_chars: int,
    rag_threshold_chars: int,
) -> None:
    """Reject invalid selector inputs with controlled domain errors."""

    if not isinstance(requested_mode, GenerationMode):
        raise DomainValidationError("requested_mode must be a GenerationMode")
    if isinstance(document_length_chars, bool) or not isinstance(document_length_chars, int):
        raise DomainValidationError("document_length_chars must be a non-negative integer")
    if document_length_chars < 0:
        raise DomainValidationError("document_length_chars must be a non-negative integer")
    if isinstance(rag_threshold_chars, bool) or not isinstance(rag_threshold_chars, int):
        raise DomainValidationError("rag_threshold_chars must be a positive integer")
    if rag_threshold_chars <= 0:
        raise DomainValidationError("rag_threshold_chars must be a positive integer")
