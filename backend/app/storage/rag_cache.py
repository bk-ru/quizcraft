"""Filesystem-backed RAG cache repository."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.generation.rag_cache import RagCacheEntry


class FileSystemRagCacheRepository:
    """Store and load RAG cache artifacts from the local filesystem."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "rag_cache"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, entry: RagCacheEntry) -> RagCacheEntry:
        """Persist a RAG cache entry to disk."""

        target_path = self._path_for_key(entry.cache_key)
        target_path.write_text(
            json.dumps(entry.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return entry

    def get(self, cache_key: str) -> RagCacheEntry:
        """Load a RAG cache entry by its cache key."""

        target_path = self._path_for_key(cache_key)
        if not target_path.exists():
            raise RepositoryNotFoundError("rag_cache", cache_key)

        try:
            payload = json.loads(target_path.read_text(encoding="utf-8"))
        except JSONDecodeError as error:
            raise DomainValidationError("rag cache artifact is malformed") from error
        if not isinstance(payload, dict):
            raise DomainValidationError("rag cache artifact is malformed")
        return RagCacheEntry.from_dict(payload)

    def exists(self, cache_key: str) -> bool:
        """Return whether a RAG cache entry exists for the supplied key."""

        return self._path_for_key(cache_key).exists()

    def delete(self, cache_key: str) -> bool:
        """Delete one RAG cache entry if it exists."""

        target_path = self._path_for_key(cache_key)
        if not target_path.exists():
            return False
        target_path.unlink()
        return True

    def _path_for_key(self, cache_key: str) -> Path:
        """Build the filesystem path for a validated cache key."""

        RagCacheEntry._validate_hash(cache_key, "cache_key")
        return self._storage_path / f"{cache_key}.json"
