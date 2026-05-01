"""RAG cache key and artifact models."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from backend.app.domain.errors import DomainValidationError
from backend.app.generation.retrieval import EmbeddedChunk
from backend.app.parsing.chunking import TextChunk


def build_document_hash(document_text: str) -> str:
    """Build a stable SHA-256 hash for normalized document text."""

    if not isinstance(document_text, str):
        raise DomainValidationError("document text must be a string")
    return hashlib.sha256(document_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RagCacheEntry:
    """Persisted RAG chunks, embeddings, and index metadata for one document configuration."""

    document_hash: str
    chunk_size: int
    chunk_overlap: int
    embedding_model_name: str
    embedded_chunks: tuple[EmbeddedChunk, ...]

    def __post_init__(self) -> None:
        """Validate cache entry invariants."""

        self._validate_hash(self.document_hash, "document_hash")
        if isinstance(self.chunk_size, bool) or not isinstance(self.chunk_size, int) or self.chunk_size <= 0:
            raise DomainValidationError("chunk_size must be a positive integer")
        if isinstance(self.chunk_overlap, bool) or not isinstance(self.chunk_overlap, int) or self.chunk_overlap < 0:
            raise DomainValidationError("chunk_overlap must be a non-negative integer")
        if self.chunk_overlap >= self.chunk_size:
            raise DomainValidationError("chunk_overlap must be smaller than chunk_size")
        if not isinstance(self.embedding_model_name, str) or not self.embedding_model_name.strip():
            raise DomainValidationError("embedding_model_name must be a non-empty string")
        object.__setattr__(self, "embedding_model_name", self.embedding_model_name.strip())
        if not isinstance(self.embedded_chunks, tuple):
            raise DomainValidationError("embedded_chunks must be a tuple")
        if not self.embedded_chunks:
            raise DomainValidationError("embedded_chunks must not be empty")
        self._validate_embedded_chunks(self.embedded_chunks)

    @property
    def cache_key(self) -> str:
        """Return the stable key for this cache artifact."""

        raw_key = "\0".join(
            (
                self.document_hash,
                str(self.chunk_size),
                str(self.chunk_overlap),
                self.embedding_model_name,
            )
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @property
    def index_metadata(self) -> dict[str, int]:
        """Return metadata needed to rebuild an in-memory vector index later."""

        return {
            "chunk_count": len(self.embedded_chunks),
            "embedding_dimension": len(self.embedded_chunks[0].embedding),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the cache entry into a JSON-compatible dictionary."""

        return {
            "cache_key": self.cache_key,
            "document_hash": self.document_hash,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model_name": self.embedding_model_name,
            "index_metadata": self.index_metadata,
            "embedded_chunks": [
                {
                    "chunk": {
                        "chunk_id": embedded_chunk.chunk.chunk_id,
                        "text": embedded_chunk.chunk.text,
                        "start_offset": embedded_chunk.chunk.start_offset,
                        "end_offset": embedded_chunk.chunk.end_offset,
                    },
                    "embedding": list(embedded_chunk.embedding),
                }
                for embedded_chunk in self.embedded_chunks
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RagCacheEntry":
        """Deserialize a cache entry from a JSON-compatible dictionary."""

        try:
            entry = cls(
                document_hash=payload["document_hash"],
                chunk_size=payload["chunk_size"],
                chunk_overlap=payload["chunk_overlap"],
                embedding_model_name=payload["embedding_model_name"],
                embedded_chunks=tuple(
                    EmbeddedChunk(
                        chunk=TextChunk(
                            chunk_id=chunk_payload["chunk"]["chunk_id"],
                            text=chunk_payload["chunk"]["text"],
                            start_offset=chunk_payload["chunk"]["start_offset"],
                            end_offset=chunk_payload["chunk"]["end_offset"],
                        ),
                        embedding=tuple(float(value) for value in chunk_payload["embedding"]),
                    )
                    for chunk_payload in payload["embedded_chunks"]
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DomainValidationError("rag cache artifact is malformed") from error

        expected_cache_key = payload.get("cache_key")
        if expected_cache_key is not None and expected_cache_key != entry.cache_key:
            raise DomainValidationError("rag cache artifact is malformed")
        expected_metadata = payload.get("index_metadata")
        if expected_metadata is not None and expected_metadata != entry.index_metadata:
            raise DomainValidationError("rag cache artifact is malformed")
        return entry

    @staticmethod
    def _validate_hash(value: str, field_name: str) -> None:
        """Validate a SHA-256 hex hash field."""

        if not isinstance(value, str) or len(value) != 64:
            raise DomainValidationError(f"{field_name} must be a SHA-256 hex string")
        try:
            int(value, 16)
        except ValueError as error:
            raise DomainValidationError(f"{field_name} must be a SHA-256 hex string") from error

    @staticmethod
    def _validate_embedded_chunks(embedded_chunks: tuple[EmbeddedChunk, ...]) -> None:
        """Validate embedded chunks and embedding dimensions."""

        expected_dimension: int | None = None
        for index, embedded_chunk in enumerate(embedded_chunks):
            if not isinstance(embedded_chunk, EmbeddedChunk):
                raise DomainValidationError(f"embedded_chunks[{index}] must be an EmbeddedChunk")
            if not isinstance(embedded_chunk.chunk, TextChunk):
                raise DomainValidationError(f"embedded_chunks[{index}].chunk must be a TextChunk")
            if not isinstance(embedded_chunk.embedding, tuple) or not embedded_chunk.embedding:
                raise DomainValidationError(f"embedded_chunks[{index}].embedding must be a non-empty tuple")
            for value in embedded_chunk.embedding:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise DomainValidationError(f"embedded_chunks[{index}].embedding must contain numbers")
            if expected_dimension is None:
                expected_dimension = len(embedded_chunk.embedding)
            elif len(embedded_chunk.embedding) != expected_dimension:
                raise DomainValidationError("all embedded_chunks must share the same embedding dimension")
