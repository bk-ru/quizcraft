"""Filesystem-backed quiz repository."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
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
        existing_quiz = self.get(quiz.quiz_id) if target_path.exists() else None
        persisted_quiz = replace(
            quiz,
            version=1 if existing_quiz is None else existing_quiz.version + 1,
            last_edited_at=self._build_last_edited_at(existing_quiz),
        )
        target_path.write_text(
            json.dumps(persisted_quiz.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return persisted_quiz

    def get(self, quiz_id: str) -> Quiz:
        """Load a quiz by its identifier."""

        target_path = self._storage_path / f"{quiz_id}.json"
        if not target_path.exists():
            raise RepositoryNotFoundError("quiz", quiz_id)

        payload = json.loads(target_path.read_text(encoding="utf-8"))
        return Quiz.from_dict(payload)

    @staticmethod
    def _build_last_edited_at(existing_quiz: Quiz | None) -> str:
        """Build a monotonically increasing UTC edit timestamp."""

        current_time = datetime.now(timezone.utc)
        if existing_quiz and existing_quiz.last_edited_at:
            previous_time = datetime.fromisoformat(existing_quiz.last_edited_at.replace("Z", "+00:00"))
            if current_time <= previous_time:
                current_time = previous_time + timedelta(microseconds=1)
        return current_time.isoformat(timespec="microseconds").replace("+00:00", "Z")
