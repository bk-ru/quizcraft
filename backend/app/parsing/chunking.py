"""Deterministic text chunking with overlap for retrieval-friendly processing."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class TextChunk:
    """One overlapping chunk of normalized text."""

    chunk_id: str
    text: str
    start_offset: int
    end_offset: int


def chunk_text(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> tuple[TextChunk, ...]:
    """Split normalized text into deterministic overlapping character chunks."""

    _validate_chunking_inputs(text, chunk_size, overlap)

    if not text:
        return ()

    step = chunk_size - overlap
    chunks: list[TextChunk] = []
    text_length = len(text)
    offset = 0
    chunk_index = 0

    while offset < text_length:
        end = min(offset + chunk_size, text_length)
        chunks.append(
            TextChunk(
                chunk_id=_format_chunk_id(chunk_index),
                text=text[offset:end],
                start_offset=offset,
                end_offset=end,
            )
        )
        chunk_index += 1
        if end == text_length:
            break
        offset += step

    return tuple(chunks)


def _validate_chunking_inputs(text: str, chunk_size: int, overlap: int) -> None:
    """Reject invalid chunker inputs with controlled domain errors."""

    if not isinstance(text, str):
        raise DomainValidationError("text must be a string")
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise DomainValidationError("chunk_size must be a positive integer")
    if isinstance(overlap, bool) or not isinstance(overlap, int):
        raise DomainValidationError("overlap must be a non-negative integer")
    if chunk_size <= 0:
        raise DomainValidationError("chunk_size must be a positive integer")
    if overlap < 0:
        raise DomainValidationError("overlap must be a non-negative integer")
    if overlap >= chunk_size:
        raise DomainValidationError("overlap must be smaller than chunk_size")


def _format_chunk_id(chunk_index: int) -> str:
    """Build a deterministic chunk identifier ordered by chunk position."""

    return f"chunk-{chunk_index:04d}"
