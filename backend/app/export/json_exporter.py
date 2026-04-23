"""Canonical JSON export for persisted quizzes."""

from __future__ import annotations

import json
from dataclasses import dataclass

from backend.app.domain.models import Quiz


@dataclass(frozen=True, slots=True)
class ExportedQuizFile:
    """Download-ready exported quiz artifact."""

    filename: str
    media_type: str
    content_bytes: bytes


class QuizJsonExporter:
    """Export persisted quizzes into deterministic JSON files."""

    media_type = "application/json; charset=utf-8"

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Render one quiz into a canonical UTF-8 JSON file."""

        payload = json.dumps(
            quiz.to_dict(),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return ExportedQuizFile(
            filename=f"{quiz.quiz_id}.json",
            media_type=self.media_type,
            content_bytes=payload,
        )
