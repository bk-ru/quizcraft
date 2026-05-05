"""CSV-экспорт сохраненных квизов, совместимый с Google Forms.

Формат колонок Google Forms:
Question, Question Type, Option 1, Option 2, ..., Option 10, Correct Answer, Points, Feedback

Поддерживаемые mappings:
- single_choice → Multiple choice со всеми вариантами
- true_false → Multiple choice с 2 вариантами: Верно, Неверно
- fill_blank → Short answer с правильным ответом в колонке Correct Answer
- short_answer → Short answer
- matching → пропускается, потому что в Google Forms нет нативного типа matching

Reference: https://support.google.com/a/answer/6191489
"""

from __future__ import annotations

import csv
import io

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.base import ExportedQuizFile


class QuizCsvExporter:
    """Экспортировать сохраненные квизы в совместимый с Google Forms UTF-8 CSV."""

    media_type = "text/csv; charset=utf-8"
    _MAX_OPTIONS = 10

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Отрендерить один квиз в CSV-файл для импорта в Google Forms."""

        output = io.StringIO(newline="")

        header = [
            "Question",
            "Question Type",
        ] + [f"Option {i}" for i in range(1, self._MAX_OPTIONS + 1)] + [
            "Correct Answer",
            "Points",
            "Feedback",
        ]

        writer = csv.writer(output)
        writer.writerow(header)

        for question in quiz.questions:
            row = self._render_question_row(question)
            if row:
                writer.writerow(row)

        content = output.getvalue().encode("utf-8")

        return ExportedQuizFile(
            filename=f"{quiz.quiz_id}.csv",
            media_type=self.media_type,
            content_bytes=content,
        )

    def _render_question_row(self, question: Question) -> list[str] | None:
        """Отрендерить один вопрос как CSV-строку для Google Forms."""

        qt = question.question_type

        if qt == "matching":
            return None

        if qt == "single_choice":
            return self._render_single_choice(question)

        if qt == "true_false":
            return self._render_true_false(question)

        if qt in {"fill_blank", "short_answer"}:
            return self._render_short_answer(question)

        raise DomainValidationError(f"unsupported question type for CSV export: {qt}")

    def _render_single_choice(self, question: Question) -> list[str]:
        """Отрендерить вопрос single_choice для Google Forms."""

        row: list[str] = [
            question.prompt,
            "Multiple choice",
        ]

        options = [opt.text for opt in question.options[:self._MAX_OPTIONS]]
        while len(options) < self._MAX_OPTIONS:
            options.append("")

        row.extend(options)

        correct = ""
        idx = question.correct_option_index
        if idx is not None and 0 <= idx < len(question.options):
            correct = question.options[idx].text

        row.append(correct)
        row.append("1")

        feedback = ""
        if question.explanation:
            feedback = question.explanation.text
        row.append(feedback)

        return row

    def _render_true_false(self, question: Question) -> list[str]:
        """Отрендерить вопрос true_false для Google Forms."""

        row: list[str] = [
            question.prompt,
            "Multiple choice",
        ]

        options = ["Верно", "Неверно"] + [""] * (self._MAX_OPTIONS - 2)
        row.extend(options)

        correct = ""
        idx = question.correct_option_index
        if idx == 0:
            correct = "Верно"
        elif idx == 1:
            correct = "Неверно"

        row.append(correct)
        row.append("1")

        feedback = ""
        if question.explanation:
            feedback = question.explanation.text
        row.append(feedback)

        return row

    def _render_short_answer(self, question: Question) -> list[str]:
        """Отрендерить вопрос fill_blank или short_answer для Google Forms."""

        row: list[str] = [
            question.prompt,
            "Short answer",
        ]

        options = [""] * self._MAX_OPTIONS
        row.extend(options)

        correct = question.correct_answer or ""
        row.append(correct)
        row.append("1")

        feedback = ""
        if question.explanation:
            feedback = question.explanation.text
        row.append(feedback)

        return row
