"""Вспомогательные средства нормализации raw payload'ов вывода модели."""

from __future__ import annotations

import re
from typing import Any

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import Explanation
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz

DEFAULT_QUIZ_ID = "quiz-generated"
DEFAULT_DOCUMENT_ID = "document-generated"
DEFAULT_QUIZ_TITLE = "Сгенерированный квиз"
DEFAULT_VERSION = 1
DEFAULT_LAST_EDITED_AT = "1970-01-01T00:00:00Z"
DEFAULT_QUESTION_TYPE = "single_choice"
GENERIC_QUIZ_TITLE_PATTERN = re.compile(r"^quiz(?:[\s_-]*\d+)?$", re.IGNORECASE)


def resolve_readable_quiz_title(
    current_title: str,
    document_filename: str,
    question_count: int,
) -> str:
    """Вернуть читаемый заголовок квиза, предпочитая вариант от LLM или генерируя из имени файла.

    Если LLM предоставила осмысленный заголовок, не пустой и не равный значению по умолчанию,
    использовать его. Иначе сгенерировать читаемый заголовок из имени файла документа
    и количества вопросов.
    """

    normalized_title = current_title.strip() if current_title else ""
    meaningful = normalized_title and normalized_title != DEFAULT_QUIZ_TITLE and not _is_generic_quiz_title(normalized_title)
    if meaningful:
        return normalized_title

    base_name = document_filename
    if "." in base_name:
        base_name = base_name.rsplit(".", 1)[0]
    base_name = base_name.replace("_", " ").replace("-", " ").strip()

    if not base_name:
        base_name = "Квиз"

    suffix = _resolve_question_count_suffix(question_count)
    return f"{base_name} — {question_count} {suffix}"


def _is_generic_quiz_title(title: str) -> bool:
    """Вернуть, является ли заголовок модели слишком общим для показа пользователям."""

    return bool(GENERIC_QUIZ_TITLE_PATTERN.fullmatch(title))


def _resolve_question_count_suffix(question_count: int) -> str:
    """Вернуть корректную русскую форму множественного числа для количества вопросов."""

    last_two_digits = abs(question_count) % 100
    if 11 <= last_two_digits <= 14:
        return "вопросов"
    last_digit = abs(question_count) % 10
    if last_digit == 1:
        return "вопрос"
    if 2 <= last_digit <= 4:
        return "вопроса"
    return "вопросов"


def normalize_quiz_output(raw_payload: dict[str, Any]) -> Quiz:
    """Нормализовать raw JSON модели в каноническую структуру квиза."""

    if not isinstance(raw_payload, dict):
        raise DomainValidationError("quiz payload must be an object")

    raw_questions = raw_payload.get("questions")
    if not isinstance(raw_questions, list):
        raise DomainValidationError("quiz payload must contain a questions list")

    questions = tuple(_normalize_question(question_payload, question_index) for question_index, question_payload in enumerate(raw_questions))
    return Quiz(
        quiz_id=_normalize_required_string(raw_payload.get("quiz_id"), default=DEFAULT_QUIZ_ID),
        document_id=_normalize_required_string(raw_payload.get("document_id"), default=DEFAULT_DOCUMENT_ID),
        title=_normalize_required_string(raw_payload.get("title"), default=DEFAULT_QUIZ_TITLE),
        version=_normalize_integer(raw_payload.get("version"), default=DEFAULT_VERSION, field_name="version"),
        last_edited_at=_normalize_required_string(raw_payload.get("last_edited_at"), default=DEFAULT_LAST_EDITED_AT),
        questions=questions,
    )


def normalize_question_output(raw_payload: dict[str, Any]) -> Question:
    """Нормализовать raw JSON модели в каноническую структуру вопроса."""

    return _normalize_question(raw_payload, 0)


def _normalize_question(raw_payload: Any, question_index: int) -> Question:
    """Нормализовать один raw payload вопроса."""

    if not isinstance(raw_payload, dict):
        raise DomainValidationError("question payload must be an object")

    question_type = _normalize_required_string(raw_payload.get("question_type"), default=DEFAULT_QUESTION_TYPE)
    raw_options = raw_payload.get("options", [])
    if not isinstance(raw_options, list):
        raise DomainValidationError("question options must be a list")

    options = tuple(
        normalized_option
        for option_position, option_payload in enumerate(raw_options)
        if (normalized_option := _normalize_option(option_payload, option_position)) is not None
    )

    if question_type in {"single_choice", "true_false"} and not options:
        has_answer = bool(_normalize_optional_string(raw_payload.get("correct_answer")))
        has_pairs = bool(raw_payload.get("matching_pairs"))
        if has_pairs:
            question_type = "matching"
        elif has_answer:
            question_type = "short_answer"

    return Question(
        question_id=_normalize_required_string(raw_payload.get("question_id"), default=f"question-{question_index + 1}"),
        question_type=question_type,
        prompt=_normalize_required_string(raw_payload.get("prompt"), default=""),
        options=options,
        correct_option_index=_normalize_correct_option_index(raw_payload, field_name="correct option"),
        correct_answer=_normalize_optional_string(raw_payload.get("correct_answer")),
        matching_pairs=_normalize_matching_pairs(raw_payload.get("matching_pairs", [])),
        explanation=_normalize_explanation(raw_payload.get("explanation")),
    )


def _normalize_option(raw_payload: Any, option_index: int) -> Option | None:
    """Нормализовать один raw payload варианта, отфильтровывая пустые варианты."""

    if not isinstance(raw_payload, dict):
        return None

    text = _normalize_required_string(raw_payload.get("text"), default="")
    if not text:
        return None

    return Option(
        option_id=_normalize_required_string(raw_payload.get("option_id"), default=f"option-{option_index + 1}"),
        text=text,
    )


def _normalize_explanation(raw_payload: Any) -> Explanation | None:
    """Нормализовать необязательный payload пояснения."""

    if raw_payload is None:
        return None

    if isinstance(raw_payload, str):
        normalized_text = raw_payload.strip()
        return None if not normalized_text else Explanation(text=normalized_text)

    if isinstance(raw_payload, dict):
        normalized_text = _normalize_required_string(raw_payload.get("text"), default="")
        return None if not normalized_text else Explanation(text=normalized_text)

    raise DomainValidationError("explanation must be null, string, or object")


def _normalize_matching_pairs(raw_payload: Any) -> tuple[MatchingPair, ...]:
    """Нормализовать payload'ы пар для сопоставления."""

    if raw_payload is None:
        return ()
    if not isinstance(raw_payload, list):
        raise DomainValidationError("matching pairs must be a list")
    pairs = []
    for pair_payload in raw_payload:
        if not isinstance(pair_payload, dict):
            continue
        left = _normalize_required_string(pair_payload.get("left"), default="")
        right = _normalize_required_string(pair_payload.get("right"), default="")
        if left and right:
            pairs.append(MatchingPair(left=left, right=right))
    return tuple(pairs)


def _normalize_optional_string(raw_value: Any) -> str | None:
    """Нормализовать необязательные строковые поля."""

    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        raise DomainValidationError("expected string field in quiz payload")
    normalized_value = raw_value.strip()
    return normalized_value or None


def _normalize_required_string(raw_value: Any, default: str) -> str:
    """Нормализовать строковое поле с обрезкой пробелов и fallback по умолчанию."""

    if raw_value is None:
        return default

    if not isinstance(raw_value, str):
        raise DomainValidationError("expected string field in quiz payload")

    normalized_value = raw_value.strip()
    return default if not normalized_value and default else normalized_value


def _normalize_integer(raw_value: Any, default: int, field_name: str) -> int:
    """Нормализовать целочисленные поля из raw значений payload."""

    if raw_value is None:
        return default

    if isinstance(raw_value, int):
        return raw_value

    if isinstance(raw_value, str) and raw_value.strip():
        try:
            return int(raw_value.strip())
        except ValueError as error:
            raise DomainValidationError(f"{field_name} must be numeric") from error

    raise DomainValidationError(f"{field_name} must be numeric")


def _normalize_correct_option_index(raw_payload: dict[str, Any], field_name: str) -> int | None:
    """Нормализовать поддерживаемые поля индекса ответа в нумерацию с нуля."""

    if "correct_option_number" in raw_payload:
        return _normalize_integer(raw_payload.get("correct_option_number"), default=1, field_name=field_name) - 1
    if "correct_option_index" in raw_payload:
        return _normalize_integer(raw_payload.get("correct_option_index"), default=0, field_name=field_name)
    return None
