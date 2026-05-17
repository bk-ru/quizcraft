"""Helpers for returning partially valid generation results."""

from __future__ import annotations

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import GenerationWarning
from backend.app.domain.models import Quiz

_DISPLAY_RECOVERY_WARNING_CODES = frozenset(
    {
        "matching_fallback_applied",
        "recovered_question_prompt",
        "replaced_placeholder_question",
        "recovered_mixed_question_fields",
    }
)
_MATCHING_ERROR_FRAGMENTS = ("соответствие", "matching", "пар")
_MATCHING_PAIR_RECOMMENDATION_FRAGMENT = "проверьте пары"
_MATCHING_REPLACED_MESSAGE = (
    "Квиз был автоматически исправлен. Вопрос на соответствие был заменён другим типом вопроса, "
    "потому что часть пар не подтверждалась текстом."
)
_MATCHING_CLEANED_MESSAGE = (
    "Квиз был автоматически исправлен. В вопросе на соответствие были удалены неподтверждённые пары."
)


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


def build_matching_fallback_warning(actions: tuple[object, ...]) -> GenerationWarning | None:
    """Build a warning that describes the local matching fallback result."""

    for action in actions:
        action_name = str(getattr(action, "action", ""))
        final_question_type = str(getattr(action, "final_question_type", ""))
        removed_pair_count = int(getattr(action, "removed_pair_count", 0) or 0)
        if final_question_type and final_question_type != "matching":
            return GenerationWarning(code="matching_fallback_applied", message=_MATCHING_REPLACED_MESSAGE)
        if action_name == "cleaned_matching" and removed_pair_count > 0:
            return GenerationWarning(code="matching_fallback_applied", message=_MATCHING_CLEANED_MESSAGE)
    return None


def merge_display_generation_warnings(
    warnings: tuple[GenerationWarning, ...],
    recovery_warnings: tuple[GenerationWarning, ...],
    final_quiz: Quiz,
) -> tuple[GenerationWarning, ...]:
    """Return warnings that describe the final displayed quiz state."""

    has_display_recovery = any(warning.code in _DISPLAY_RECOVERY_WARNING_CODES for warning in recovery_warnings)
    final_has_matching = any(question.question_type == "matching" for question in final_quiz.questions)
    filtered_warnings: list[GenerationWarning] = []
    for warning in warnings:
        if has_display_recovery and _is_recoverable_matching_warning(warning):
            continue
        filtered_warnings.append(_without_pair_recommendation(warning) if not final_has_matching else warning)
    if has_display_recovery:
        return (*recovery_warnings, *tuple(filtered_warnings))
    return (*tuple(filtered_warnings), *recovery_warnings)


def _is_recoverable_matching_warning(warning: GenerationWarning) -> bool:
    message = warning.message.casefold()
    return warning.code == "generation_quality_error" and any(
        fragment in message for fragment in _MATCHING_ERROR_FRAGMENTS
    )


def _without_pair_recommendation(warning: GenerationWarning) -> GenerationWarning:
    recommendations = tuple(
        item
        for item in warning.recommendations
        if _MATCHING_PAIR_RECOMMENDATION_FRAGMENT not in item.casefold()
    )
    if recommendations == warning.recommendations:
        return warning
    return GenerationWarning(code=warning.code, message=warning.message, recommendations=recommendations)


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
