"""Helpers for returning partially valid generation results."""

from __future__ import annotations

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import GenerationWarning


def build_partial_generation_warning(
    error: DomainValidationError,
    *,
    expected_question_count: int,
    actual_question_count: int,
) -> GenerationWarning:
    """Build a user-facing warning for a normalized but partially valid quiz."""

    if isinstance(error, GenerationQualityError) and "question count" in error.message:
        return GenerationWarning(
            code=error.code,
            message=(
                f"Модель вернула {actual_question_count} "
                f"{_question_word(actual_question_count)} вместо запрошенных {expected_question_count}; "
                "показан частичный квиз."
            ),
            recommendations=(
                "Проверьте результат, повторите генерацию или уменьшите количество вопросов.",
                "Если нужен точный объём, попробуйте strict-профиль или выберите меньше типов вопросов.",
            ),
        )

    return GenerationWarning(
        code=error.code,
        message=f"Квиз показан с предупреждением: {error.message}",
        recommendations=(
            "Проверьте показанный квиз перед использованием.",
            "Если предупреждение связано с соответствием, проверьте пары и повторите генерацию.",
        ),
    )


def _question_word(count: int) -> str:
    normalized = abs(count) % 100
    if 11 <= normalized <= 14:
        return "вопросов"
    last_digit = normalized % 10
    if last_digit == 1:
        return "вопрос"
    if 2 <= last_digit <= 4:
        return "вопроса"
    return "вопросов"
