"""Business validation for domain entities."""

from __future__ import annotations

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Quiz


def validate_quiz(quiz: Quiz) -> None:
    """Validate that a quiz satisfies core business rules."""

    if not quiz.title.strip():
        raise DomainValidationError("quiz title must not be empty")

    if not quiz.questions:
        raise DomainValidationError("quiz must contain at least one question")

    for question in quiz.questions:
        if not question.prompt.strip():
            raise DomainValidationError("question prompt must not be empty")

        if len(question.options) < 2:
            raise DomainValidationError("question must have at least two options")

        if any(not option.text.strip() for option in question.options):
            raise DomainValidationError("option text must not be empty")

        normalized_options = {option.text.strip().casefold() for option in question.options}
        if len(normalized_options) != len(question.options):
            raise DomainValidationError("question options must not contain duplicates")

        if question.correct_option_index < 0 or question.correct_option_index >= len(question.options):
            raise DomainValidationError("correct option index is out of range")
