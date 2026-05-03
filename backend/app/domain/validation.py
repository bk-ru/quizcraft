"""Business validation for domain entities."""

from __future__ import annotations

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Quiz

CHOICE_QUESTION_TYPES = frozenset({"single_choice", "true_false"})
ANSWER_QUESTION_TYPES = frozenset({"fill_blank", "short_answer"})
SUPPORTED_QUESTION_TYPES = CHOICE_QUESTION_TYPES | ANSWER_QUESTION_TYPES | frozenset({"matching"})


def validate_quiz(quiz: Quiz) -> None:
    """Validate that a quiz satisfies core business rules."""

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
                raise DomainValidationError("question options must not contain duplicates")

            if question.correct_option_index is None:
                raise DomainValidationError("correct option index is required")
            if question.correct_option_index < 0 or question.correct_option_index >= len(question.options):
                raise DomainValidationError("correct option index is out of range")

        if question_type in ANSWER_QUESTION_TYPES:
            if not isinstance(question.correct_answer, str) or not question.correct_answer.strip():
                raise DomainValidationError("correct answer must not be empty")

        if question_type == "matching":
            if not question.matching_pairs:
                raise DomainValidationError("matching question must contain at least one pair")
            for pair in question.matching_pairs:
                if not pair.left.strip() or not pair.right.strip():
                    raise DomainValidationError("matching pair values must not be empty")
