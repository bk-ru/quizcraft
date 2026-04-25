"""Embedding chunks, in-memory vector index, and top-k cosine retriever."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import EmbeddingRequest
from backend.app.llm.provider import LLMProvider
from backend.app.parsing.chunking import TextChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    """A chunk paired with its embedding vector."""

    chunk: TextChunk
    embedding: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    """A retrieved chunk paired with its similarity score."""

    chunk: TextChunk
    score: float


def embed_chunks(
    chunks: Sequence[TextChunk],
    *,
    provider: LLMProvider,
    model_name: str | None = None,
    batch_size: int = 32,
) -> tuple[EmbeddedChunk, ...]:
    """Generate embeddings for the supplied chunks via the provider."""

    _validate_embed_chunks_inputs(chunks, batch_size)

    if not chunks:
        return ()

    embedded: list[EmbeddedChunk] = []
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        request = EmbeddingRequest(
            texts=tuple(chunk.text for chunk in batch),
            model_name=model_name,
        )
        response = provider.embed(request)
        if len(response.vectors) != len(batch):
            raise DomainValidationError(
                "embeddings response length does not match the number of chunks"
            )
        for chunk, vector in zip(batch, response.vectors, strict=True):
            embedded.append(EmbeddedChunk(chunk=chunk, embedding=vector))

    logger.info("Embedded %s chunks via provider model", len(embedded))
    return tuple(embedded)


def _validate_embed_chunks_inputs(chunks: Sequence[TextChunk], batch_size: int) -> None:
    """Reject invalid embed_chunks inputs with controlled domain errors."""

    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise DomainValidationError("batch_size must be a positive integer")
    if batch_size <= 0:
        raise DomainValidationError("batch_size must be a positive integer")
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, TextChunk):
            raise DomainValidationError(f"chunks[{index}] must be a TextChunk")


class InMemoryVectorIndex:
    """Local vector index backed by per-chunk cosine similarity search."""

    def __init__(self, embedded_chunks: Sequence[EmbeddedChunk]) -> None:
        validated_chunks = self._validate_embedded_chunks(embedded_chunks)
        self._embedded_chunks: tuple[EmbeddedChunk, ...] = validated_chunks
        self._dimension = (
            len(validated_chunks[0].embedding) if validated_chunks else 0
        )

    def __len__(self) -> int:
        """Return the number of embedded chunks held by the index."""

        return len(self._embedded_chunks)

    @property
    def dimension(self) -> int:
        """Return the embedding dimension shared by indexed vectors."""

        return self._dimension

    @property
    def embedded_chunks(self) -> tuple[EmbeddedChunk, ...]:
        """Return the embedded chunks held by the index in insertion order."""

        return self._embedded_chunks

    def search(
        self,
        query_vector: Sequence[float],
        *,
        top_k: int,
    ) -> tuple[ScoredChunk, ...]:
        """Return the top-`top_k` chunks ordered by descending similarity."""

        self._validate_search_inputs(query_vector, top_k)

        if not self._embedded_chunks:
            return ()

        scored_with_position: list[tuple[float, int, ScoredChunk]] = []
        for position, embedded_chunk in enumerate(self._embedded_chunks):
            similarity = _cosine_similarity(query_vector, embedded_chunk.embedding)
            scored_with_position.append(
                (
                    similarity,
                    position,
                    ScoredChunk(chunk=embedded_chunk.chunk, score=similarity),
                )
            )

        scored_with_position.sort(key=lambda item: (-item[0], item[1]))
        limit = min(top_k, len(scored_with_position))
        return tuple(scored for _, _, scored in scored_with_position[:limit])

    @staticmethod
    def _validate_embedded_chunks(
        embedded_chunks: Sequence[EmbeddedChunk],
    ) -> tuple[EmbeddedChunk, ...]:
        """Validate the embedded chunks and freeze them as a tuple."""

        materialized: list[EmbeddedChunk] = []
        expected_dimension: int | None = None
        for index, embedded_chunk in enumerate(embedded_chunks):
            if not isinstance(embedded_chunk, EmbeddedChunk):
                raise DomainValidationError(
                    f"embedded_chunks[{index}] must be an EmbeddedChunk"
                )
            if not isinstance(embedded_chunk.embedding, tuple):
                raise DomainValidationError(
                    f"embedded_chunks[{index}].embedding must be a tuple of floats"
                )
            if not embedded_chunk.embedding:
                raise DomainValidationError(
                    f"embedded_chunks[{index}].embedding must not be empty"
                )
            if expected_dimension is None:
                expected_dimension = len(embedded_chunk.embedding)
            elif len(embedded_chunk.embedding) != expected_dimension:
                raise DomainValidationError(
                    "all embedded_chunks must share the same embedding dimension"
                )
            materialized.append(embedded_chunk)
        return tuple(materialized)

    def _validate_search_inputs(
        self,
        query_vector: Sequence[float],
        top_k: int,
    ) -> None:
        """Reject invalid search inputs with controlled domain errors."""

        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise DomainValidationError("top_k must be a positive integer")
        if top_k <= 0:
            raise DomainValidationError("top_k must be a positive integer")
        if not isinstance(query_vector, Sequence) or isinstance(query_vector, str):
            raise DomainValidationError("query_vector must be a sequence of floats")
        if not query_vector:
            raise DomainValidationError("query_vector must not be empty")
        if self._embedded_chunks and len(query_vector) != self._dimension:
            raise DomainValidationError(
                "query_vector dimension does not match the index dimension"
            )


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""

    if len(left) != len(right):
        raise DomainValidationError("vectors must share the same dimension")

    dot_product = 0.0
    left_norm_squared = 0.0
    right_norm_squared = 0.0
    for left_value, right_value in zip(left, right, strict=True):
        dot_product += left_value * right_value
        left_norm_squared += left_value * left_value
        right_norm_squared += right_value * right_value

    if left_norm_squared <= 0.0 or right_norm_squared <= 0.0:
        return 0.0

    return dot_product / math.sqrt(left_norm_squared * right_norm_squared)
