"""Канонический JSON-экспорт для сохраненных квизов."""

from __future__ import annotations

import json

from backend.app.domain.models import Quiz
from backend.app.export.base import ExportedQuizFile


class QuizJsonExporter:
    """Экспортировать сохраненные квизы в детерминированные JSON-файлы."""

    media_type = "application/json; charset=utf-8"

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Отрендерить один квиз в канонический UTF-8 JSON-файл."""

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
