"""Проверки качества нормализованного вывода квиза."""

from __future__ import annotations

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import Quiz
from backend.app.domain.validation import validate_quiz

_DOC_LENGTH_THRESHOLDS: tuple[tuple[int, int], ...] = (
    (300, 2),
    (800, 5),
    (2000, 10),
    (5000, 15),
)


def enrich_generation_error(error: DomainValidationError, doc_char_count: int) -> DomainValidationError:
    """Вернуть новую ошибку с подсказкой о длине документа, когда текст короткий."""

    for max_chars, max_questions in _DOC_LENGTH_THRESHOLDS:
        if doc_char_count < max_chars:
            hint = (
                f" Текст документа слишком короткий ({doc_char_count} символов) — "
                f"рекомендуется не более {max_questions} вопросов. "
                f"Попробуйте уменьшить количество вопросов или добавить больше текста."
            )
            return type(error)(error.message + hint)
    return error


class GenerationQualityChecker:
    """Проверить нормализованный вывод квиза по правилам качества после генерации."""

    def ensure_quality(self, quiz: Quiz, expected_question_count: int) -> None:
        """Вызвать контролируемую доменную ошибку, когда квиз не проходит проверки качества."""

        validate_quiz(quiz)
        if len(quiz.questions) != expected_question_count:
            raise GenerationQualityError(
                "generated quiz question count does not match the requested question count"
            )

        seen_prompts: set[str] = set()
        for question in quiz.questions:
            normalized_prompt = question.prompt.strip().casefold()
            if normalized_prompt in seen_prompts:
                raise GenerationQualityError("generated quiz contains duplicate question prompts")
            seen_prompts.add(normalized_prompt)
