"""Quality checks for normalized quiz output."""

from __future__ import annotations

from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import Quiz
from backend.app.domain.validation import validate_quiz


class GenerationQualityChecker:
    """Validate normalized quiz output against post-generation quality rules."""

    def ensure_quality(self, quiz: Quiz, expected_question_count: int) -> None:
        """Raise a controlled domain error when the quiz fails quality checks."""

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
