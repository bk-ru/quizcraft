"""PPTX export for persisted quizzes."""

from __future__ import annotations

from io import BytesIO

from pptx import Presentation
from pptx.util import Inches
from pptx.util import Pt

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.base import ExportedQuizFile


class QuizPptxExporter:
    """Export persisted quizzes into PPTX files."""

    media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Render one quiz into a PPTX file."""

        presentation = Presentation()
        for question_index, question in enumerate(quiz.questions, start=1):
            self._add_question_slide(presentation, quiz.title, question, question_index)
        output = BytesIO()
        presentation.save(output)
        return ExportedQuizFile(
            filename=f"{quiz.quiz_id}.pptx",
            media_type=self.media_type,
            content_bytes=output.getvalue(),
        )

    def _add_question_slide(self, presentation, quiz_title: str, question: Question, question_index: int) -> None:
        correct_option = self._resolve_correct_option(question)
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.35), Inches(9), Inches(0.55))
        title_frame = title_box.text_frame
        title_frame.text = quiz_title
        title_frame.paragraphs[0].runs[0].font.size = Pt(20)
        body_box = slide.shapes.add_textbox(Inches(0.7), Inches(1.05), Inches(8.6), Inches(5.9))
        body_frame = body_box.text_frame
        body_frame.word_wrap = True
        self._add_body_line(body_frame, f"Вопрос {question_index}", Pt(18))
        self._add_body_line(body_frame, question.prompt, Pt(16))
        self._add_body_line(body_frame, "Варианты:", Pt(14))
        for option_index, option in enumerate(question.options, start=1):
            self._add_body_line(body_frame, f"{option_index}. {option.text}", Pt(14))
        self._add_body_line(body_frame, f"Правильный ответ: {correct_option.text}", Pt(14))
        if question.explanation is not None:
            self._add_body_line(body_frame, f"Пояснение: {question.explanation.text}", Pt(14))

    @staticmethod
    def _add_body_line(text_frame, text: str, font_size) -> None:
        paragraph = text_frame.add_paragraph()
        paragraph.text = text
        paragraph.font.size = font_size

    @staticmethod
    def _resolve_correct_option(question: Question) -> Option:
        if question.correct_option_index < 0 or question.correct_option_index >= len(question.options):
            raise DomainValidationError(
                f"question '{question.question_id}' has invalid correct_option_index for PPTX export"
            )
        return question.options[question.correct_option_index]
