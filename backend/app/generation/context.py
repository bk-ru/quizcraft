"""Bounded context assembler for retrieval-augmented generation."""

from __future__ import annotations

from collections.abc import Sequence

from backend.app.domain.errors import DomainValidationError
from backend.app.generation.retrieval import ScoredChunk


def assemble_context(
    scored_chunks: Sequence[ScoredChunk],
    *,
    max_chars: int,
    separator: str = "\n\n",
) -> str:
    """Build a bounded context block from retrieved chunks in supplied order."""

    _validate_assemble_context_inputs(scored_chunks, max_chars, separator)

    if not scored_chunks:
        return ""

    accumulated_parts: list[str] = []
    accumulated_length = 0

    for scored_chunk in scored_chunks:
        chunk_text = scored_chunk.chunk.text
        addition_length = len(chunk_text) + (len(separator) if accumulated_parts else 0)
        if accumulated_length + addition_length > max_chars:
            if not accumulated_parts:
                return chunk_text[:max_chars]
            break
        accumulated_parts.append(chunk_text)
        accumulated_length += addition_length

    return separator.join(accumulated_parts)


def _validate_assemble_context_inputs(
    scored_chunks: Sequence[ScoredChunk],
    max_chars: int,
    separator: str,
) -> None:
    """Reject invalid context assembler inputs with controlled domain errors."""

    if isinstance(max_chars, bool) or not isinstance(max_chars, int):
        raise DomainValidationError("max_chars must be a positive integer")
    if max_chars <= 0:
        raise DomainValidationError("max_chars must be a positive integer")
    if not isinstance(separator, str):
        raise DomainValidationError("separator must be a string")
    for index, scored_chunk in enumerate(scored_chunks):
        if not isinstance(scored_chunk, ScoredChunk):
            raise DomainValidationError(
                f"scored_chunks[{index}] must be a ScoredChunk"
            )
