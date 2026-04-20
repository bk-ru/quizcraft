"""Filesystem-backed generation-result repository."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import GenerationResult


class FileSystemGenerationResultRepository:
    """Store and load generation results from the local filesystem."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "generation_results"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, result: GenerationResult) -> GenerationResult:
        """Persist a generation result to disk."""

        target_path = self._storage_path / f"{result.quiz.quiz_id}.json"
        target_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    def get(self, quiz_id: str) -> GenerationResult:
        """Load a generation result by the generated quiz identifier."""

        target_path = self._storage_path / f"{quiz_id}.json"
        if not target_path.exists():
            raise RepositoryNotFoundError("generation_result", quiz_id)

        payload = json.loads(target_path.read_text(encoding="utf-8"))
        return GenerationResult.from_dict(payload)
