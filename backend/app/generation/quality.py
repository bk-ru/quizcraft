"""Проверки качества нормализованного вывода квиза."""

from __future__ import annotations

from dataclasses import replace

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import Quiz
from backend.app.domain.validation import validate_quiz
from backend.app.generation.matching_grounding import MATCHING_GROUNDEDNESS_ERROR_MESSAGE
from backend.app.generation.matching_grounding import is_matching_pair_grounded
from backend.app.generation.matching_grounding import normalize_grounding_text
from backend.app.generation.question_quality import ensure_methodical_quality

_DOC_LENGTH_THRESHOLDS: tuple[tuple[int, int], ...] = (
    (300, 2),
    (800, 5),
    (2000, 10),
    (5000, 15),
)


def fit_generated_question_count(quiz: Quiz, expected_question_count: int) -> Quiz:
    """Return a quiz with no more than the requested number of questions."""

    if len(quiz.questions) > expected_question_count:
        return replace(quiz, questions=quiz.questions[:expected_question_count])
    return quiz


def enrich_generation_error(
    error: DomainValidationError,
    doc_char_count: int,
    requested_question_count: int | None = None,
) -> DomainValidationError:
    """Вернуть новую ошибку с подсказкой о длине документа, когда текст короткий."""

    for max_chars, max_questions in _DOC_LENGTH_THRESHOLDS:
        if doc_char_count < max_chars:
            if requested_question_count is not None and requested_question_count <= max_questions:
                return error
            hint = (
                f" Текст документа слишком короткий ({doc_char_count} символов) — "
                f"рекомендуется не более {max_questions} вопросов. "
                f"Попробуйте уменьшить количество вопросов или добавить больше текста."
            )
            return type(error)(error.message + hint)
    return error


class GenerationQualityChecker:
    """Проверить нормализованный вывод квиза по правилам качества после генерации."""

    def ensure_quality(
        self,
        quiz: Quiz,
        expected_question_count: int,
        *,
        source_text: str | None = None,
        allow_partial: bool = False,
    ) -> None:
        """Вызвать контролируемую доменную ошибку, когда квиз не проходит проверки качества."""

        validate_quiz(quiz)
        ensure_methodical_quality(quiz)
        if source_text:
            _ensure_matching_pairs_are_grounded(quiz, source_text)
        if len(quiz.questions) != expected_question_count and not allow_partial:
            raise GenerationQualityError(
                "generated quiz question count does not match the requested question count"
            )

        seen_prompts: set[str] = set()
        for question in quiz.questions:
            normalized_prompt = question.prompt.strip().casefold()
            if normalized_prompt in seen_prompts:
                raise GenerationQualityError("generated quiz contains duplicate question prompts")
            seen_prompts.add(normalized_prompt)


def _ensure_matching_pairs_are_grounded(quiz: Quiz, source_text: str) -> None:
    source = normalize_grounding_text(source_text)
    if not source:
        return
    for question in quiz.questions:
        if question.question_type != "matching":
            continue
        for pair in question.matching_pairs:
            if not is_matching_pair_grounded(pair, source):
                raise GenerationQualityError(MATCHING_GROUNDEDNESS_ERROR_MESSAGE)
