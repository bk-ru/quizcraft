"""Бизнес-валидация доменных сущностей."""

from __future__ import annotations

import logging

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Quiz

logger = logging.getLogger(__name__)

CHOICE_QUESTION_TYPES = frozenset({"single_choice", "true_false"})
ANSWER_QUESTION_TYPES = frozenset({"fill_blank", "short_answer"})
SUPPORTED_QUESTION_TYPES = CHOICE_QUESTION_TYPES | ANSWER_QUESTION_TYPES | frozenset({"matching"})
MATCHING_SYMBOLIC_RIGHT_VALUES = frozenset({"a", "b", "c", "d", "1", "2", "3", "4"})


def validate_quiz(quiz: Quiz) -> None:
    """Проверить, что квиз соответствует основным бизнес-правилам."""

    if not quiz.title.strip():
        raise DomainValidationError("quiz title must not be empty")

    if not quiz.questions:
        raise DomainValidationError("quiz must contain at least one question")

    for question in quiz.questions:
        if not question.prompt.strip():
            raise DomainValidationError("question prompt must not be empty")

        question_type = question.question_type.strip() if isinstance(question.question_type, str) else ""
        if question_type not in SUPPORTED_QUESTION_TYPES:
            raise DomainValidationError(f"unsupported question type: {question.question_type}")

        if question_type in CHOICE_QUESTION_TYPES:
            if len(question.options) < 2:
                raise DomainValidationError("question must have at least two options")

            if any(not option.text.strip() for option in question.options):
                raise DomainValidationError("option text must not be empty")

            normalized_options = {option.text.strip().casefold() for option in question.options}
            if len(normalized_options) != len(question.options):
                duplicate_texts = [
                    opt.text for opt in question.options
                    if sum(1 for o in question.options if o.text.strip().casefold() == opt.text.strip().casefold()) > 1
                ]
                logger.warning(
                    "Quiz %s question %s has duplicate options: %s",
                    quiz.quiz_id,
                    question.question_id,
                    list(set(duplicate_texts)),
                )

            if question.correct_option_index is None:
                raise DomainValidationError("correct option index is required")
            if question.correct_option_index < 0 or question.correct_option_index >= len(question.options):
                raise DomainValidationError("correct option index is out of range")

        if question_type in ANSWER_QUESTION_TYPES:
            if not isinstance(question.correct_answer, str) or not question.correct_answer.strip():
                raise DomainValidationError("correct answer must not be empty")

        if question_type == "matching":
            if question.options:
                raise DomainValidationError("matching question must not include options")
            if question.correct_option_index is not None:
                raise DomainValidationError("matching question correct option index must be empty")
            if question.correct_answer is not None:
                raise DomainValidationError("matching question correct answer must be empty")
            if len(question.matching_pairs) < 4:
                raise DomainValidationError("matching question must have at least four pairs")
            for pair in question.matching_pairs:
                if not pair.left.strip() or not pair.right.strip():
                    raise DomainValidationError("matching pair values must not be empty")
                if pair.right.strip().casefold() in MATCHING_SYMBOLIC_RIGHT_VALUES:
                    raise DomainValidationError("matching pair right must contain full text, not an option id")
