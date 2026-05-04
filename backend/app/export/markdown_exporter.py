"""Markdown export for persisted quizzes — human-readable plain text.

Supports all question types:
- single_choice: enumerated options
- true_false: simplified boolean
- fill_blank: inline blank marker
- short_answer: correct answer shown
- matching: two-column table
"""

from __future__ import annotations

from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.export.base import ExportedQuizFile


def _escape_md(text: str) -> str:
    """Escape markdown special characters in text."""

    chars = ["\\", "`", "*", "_", "{", "}", "[", "]", "<", ">", "(", ")", "#", "+", "-", ".", "!", "|"]
    for char in chars:
        text = text.replace(char, f"\\{char}")
    return text


class QuizMarkdownExporter:
    """Export persisted quizzes into clean UTF-8 Markdown."""

    media_type = "text/markdown; charset=utf-8"

    def export(self, quiz: Quiz) -> ExportedQuizFile:
        """Render one quiz into a UTF-8 Markdown file."""

        lines: list[str] = []

        title = _escape_md(quiz.title)
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"**ID квиза:** `{quiz.quiz_id}`  ")
        lines.append(f"**ID документа:** `{quiz.document_id}`  ")
        lines.append(f"**Версия:** {quiz.version}  ")
        lines.append(f"**Последнее изменение:** {quiz.last_edited_at}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, question in enumerate(quiz.questions, start=1):
            lines.extend(self._render_question(question, i))
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Ответы")
        lines.append("")

        for i, question in enumerate(quiz.questions, start=1):
            lines.append(self._render_answer_line(question, i))

        content = "\n".join(lines).encode("utf-8")

        return ExportedQuizFile(
            filename=f"{quiz.quiz_id}.md",
            media_type=self.media_type,
            content_bytes=content,
        )

    def _render_question(self, question: Question, index: int) -> list[str]:
        """Render one question in markdown format."""

        lines: list[str] = []
        qt = question.question_type

        prompt = _escape_md(question.prompt)
        lines.append(f"### Вопрос {index}")
        lines.append("")
        lines.append(f"**Тип:** {self._type_label(qt)}  ")
        lines.append(f"**ID:** `{question.question_id}`")
        lines.append("")
        lines.append(f"{prompt}")
        lines.append("")

        if qt == "single_choice":
            for j, option in enumerate(question.options, start=1):
                label = chr(0x40 + j)
                text = _escape_md(option.text)
                lines.append(f"{label}. {text}")

        elif qt == "true_false":
            lines.append("A. Верно")
            lines.append("B. Неверно")

        elif qt == "matching":
            lines.append("| Левая колонка | Правая колонка |")
            lines.append("| --- | --- |")
            for pair in question.matching_pairs:
                left = _escape_md(pair.left)
                right = _escape_md(pair.right)
                lines.append(f"| {left} | {right} |")

        elif qt in {"fill_blank", "short_answer"}:
            answer = question.correct_answer or "(нет ответа)"
            lines.append(f"**Правильный ответ:** {_escape_md(answer)}")

        if question.explanation:
            lines.append("")
            lines.append(f"*Пояснение: {_escape_md(question.explanation.text)}*")

        return lines

    def _render_answer_line(self, question: Question, index: int) -> str:
        """Render compact answer line for answer key section."""

        qt = question.question_type

        if qt == "matching":
            pairs = [f"{p.left} → {p.right}" for p in question.matching_pairs]
            answer = "; ".join(pairs)
        elif qt in {"fill_blank", "short_answer"}:
            answer = question.correct_answer or "(нет ответа)"
        elif qt == "true_false":
            idx = question.correct_option_index
            answer = "Верно" if idx == 0 else "Неверно"
        else:
            idx = question.correct_option_index
            if idx is not None and 0 <= idx < len(question.options):
                label = chr(0x41 + idx)
                text = question.options[idx].text
                answer = f"{label}. {text}"
            else:
                answer = "(не указан)"

        prompt_short = question.prompt[:40] + "…" if len(question.prompt) > 40 else question.prompt
        return f"**{index}.** {prompt_short} — `{answer}`"

    @staticmethod
    def _type_label(qt: str) -> str:
        """Return human-readable type label in Russian."""

        labels = {
            "single_choice": "Одиночный выбор",
            "true_false": "Верно/Неверно",
            "fill_blank": "Заполнить пропуск",
            "short_answer": "Краткий ответ",
            "matching": "Соответствие",
        }
        return labels.get(qt, qt)
