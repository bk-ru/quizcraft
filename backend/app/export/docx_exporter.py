"""DOCX export for persisted quizzes."""

from __future__ import annotations

from io import BytesIO

from docx import Document

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.base import ExportedQuizFile


class QuizDocxExporter:
    """Export persisted quizzes into DOCX files."""

    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Render one quiz into a DOCX file."""

        document = Document()
        document.add_heading(quiz.title, level=1)
        for question_index, question in enumerate(quiz.questions, start=1):
            self._add_question(document, question, question_index)
        output = BytesIO()
        document.save(output)
        return ExportedQuizFile(
            filename=f"{quiz.quiz_id}.docx",
            media_type=self.media_type,
            content_bytes=output.getvalue(),
        )

    def _add_question(self, document, question: Question, question_index: int) -> None:
        document.add_heading(f"Вопрос {question_index}", level=2)
        document.add_paragraph(question.prompt)
        if question.question_type == "matching":
            for pair in question.matching_pairs:
                document.add_paragraph(f"{pair.left} — {pair.right}")
        elif question.question_type in {"fill_blank", "short_answer"}:
            document.add_paragraph(f"Правильный ответ: {question.correct_answer}")
        else:
            correct_option = self._resolve_correct_option(question)
            for option_index, option in enumerate(question.options, start=1):
                document.add_paragraph(f"{option_index}. {option.text}")
            document.add_paragraph(f"Правильный ответ: {correct_option.text}")
        if question.explanation is not None:
            document.add_paragraph(f"Пояснение: {question.explanation.text}")

    @staticmethod
    def _resolve_correct_option(question: Question) -> Option:
        if (
            question.correct_option_index is None
            or question.correct_option_index < 0
            or question.correct_option_index >= len(question.options)
        ):
            raise DomainValidationError(
                f"question '{question.question_id}' has invalid correct_option_index for DOCX export"
            )
        return question.options[question.correct_option_index]
