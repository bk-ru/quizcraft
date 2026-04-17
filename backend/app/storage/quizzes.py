"""Filesystem-backed quiz repository."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import Quiz


class FileSystemQuizRepository:
    """Store and load quizzes from the local filesystem."""

    def __init__(self, root_path: Path) -> None:
        self._storage_path = Path(root_path) / "quizzes"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, quiz: Quiz) -> Quiz:
        """Persist a quiz to disk."""

        target_path = self._storage_path / f"{quiz.quiz_id}.json"
        target_path.write_text(json.dumps(quiz.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        return quiz

    def get(self, quiz_id: str) -> Quiz:
        """Load a quiz by its identifier."""

        target_path = self._storage_path / f"{quiz_id}.json"
        if not target_path.exists():
            raise RepositoryNotFoundError("quiz", quiz_id)

        payload = json.loads(target_path.read_text(encoding="utf-8"))
        return Quiz.from_dict(payload)
