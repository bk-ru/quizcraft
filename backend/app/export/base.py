"""Common contracts for quiz export artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.models import Quiz


@dataclass(frozen=True, slots=True)
class ExportedQuizFile:
    """Download-ready exported quiz artifact."""

    filename: str
    media_type: str
    content_bytes: bytes


class QuizExporter(Protocol):
    """Exporter contract for persisted quizzes."""

    media_type: str

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Render one quiz into a download-ready artifact."""
