"""Общие контракты для артефактов экспорта квиза."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.models import Quiz


@dataclass(frozen=True, slots=True)
class ExportedQuizFile:
    """Готовый к скачиванию экспортированный артефакт квиза."""

    filename: str
    media_type: str
    content_bytes: bytes


class QuizExporter(Protocol):
    """Контракт экспортера для сохраненных квизов."""

    media_type: str

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Отрендерить один квиз в готовый к скачиванию артефакт."""
