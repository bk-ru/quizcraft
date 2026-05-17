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
    """Нормализовать raw JSON модели в каноническую структуру квиза.

    Сохраняет совместимость с известными структурными ошибками LLM.
    """

    if not isinstance(raw_payload, dict):
        raise DomainValidationError("quiz payload must be an object")

    raw_questions = _read_payload_value(raw_payload, "questions", default=[])
    if not isinstance(raw_questions, list):
        raw_questions = []
    return Quiz(
        quiz_id=_normalize_required_string(
            _read_payload_value(raw_payload, "quiz_id", "quizId"),
            default=DEFAULT_QUIZ_ID,
        ),
        document_id=_normalize_required_string(
            _read_payload_value(raw_payload, "document_id", "documentId"),
            default=DEFAULT_DOCUMENT_ID,
        ),
        title=_normalize_required_string(
            _read_payload_value(raw_payload, "title"),
            default=DEFAULT_QUIZ_TITLE,
        ),
        version=_normalize_integer(
            _read_payload_value(raw_payload, "version"),
            default=DEFAULT_VERSION,
            field_name="version",
        ),
        last_edited_at=_normalize_required_string(
            _read_payload_value(raw_payload, "last_edited_at", "lastEditedAt"),
            default=DEFAULT_LAST_EDITED_AT,
        ),
        questions=tuple(_normalize_question(question, index) for index, question in enumerate(raw_questions)),
    )


def normalize_question_output(raw_payload: dict[str, Any]) -> Question:
    """Нормализовать raw JSON модели в каноническую структуру вопроса."""

    return _normalize_question(raw_payload, 0)


def _normalize_question(raw_payload: Any, question_index: int) -> Question:
    """Нормализовать один raw payload вопроса."""

    if not isinstance(raw_payload, dict):
        raise DomainValidationError("question payload must be an object")

    question_type = _normalize_required_string(
        _read_payload_value(raw_payload, "question_type", "questionType"),
        default=DEFAULT_QUESTION_TYPE,
    )
    raw_options = _read_payload_value(raw_payload, "options", default=[])
    if not isinstance(raw_options, list):
        raise DomainValidationError("question options must be a list")

    has_explicit_index = any(
        key in raw_payload
        for key in (
            "correct_option_number",
            "correctOptionNumber",
            "correct_option_index",
            "correctOptionIndex",
        )
    )
    inlined_index = _extract_inlined_correct_option_index(raw_options)
    if not has_explicit_index and inlined_index is not None and _has_trailing_duplicate_option(raw_options):
        raw_options = raw_options[:-1]

    options = tuple(
        normalized_option
        for option_position, option_payload in enumerate(raw_options)
        if (normalized_option := _normalize_option(option_payload, option_position)) is not None
    )

    if question_type in {"single_choice", "true_false"} and not options:
        has_answer = bool(
            _normalize_optional_string(_read_payload_value(raw_payload, "correct_answer", "correctAnswer"))
        )
        has_pairs = bool(_read_payload_value(raw_payload, "matching_pairs", "matchingPairs", default=[]))
        if has_pairs:
            question_type = "matching"
        elif has_answer and question_type != "true_false":
            question_type = "short_answer"

    if question_type == "true_false" and not options:
        options = _make_true_false_options()
        if inlined_index is None:
            inlined_index = _resolve_true_false_index(raw_payload)

    explicit_index = _normalize_correct_option_index(raw_payload, field_name="correctOptionIndex")
    resolved_index = explicit_index if explicit_index is not None else inlined_index
    correct_answer = _normalize_optional_string(_read_payload_value(raw_payload, "correct_answer", "correctAnswer"))
    if question_type in {"single_choice", "true_false"}:
        correct_answer = None

    return Question(
        question_id=_normalize_required_string(
            _read_payload_value(raw_payload, "question_id", "questionId"),
            default=f"question-{question_index + 1}",
        ),
        question_type=question_type,
        prompt=_normalize_required_string(_read_payload_value(raw_payload, "prompt"), default=""),
        options=options,
        correct_option_index=resolved_index,
        correct_answer=correct_answer,
        matching_pairs=_normalize_matching_pairs(
            _read_payload_value(raw_payload, "matching_pairs", "matchingPairs", default=[])
        ),
        explanation=_normalize_explanation(_read_payload_value(raw_payload, "explanation")),
    )


def _normalize_option(raw_payload: Any, option_index: int) -> Option | None:
    """Нормализовать один raw payload варианта, отфильтровывая пустые варианты."""

    if not isinstance(raw_payload, dict):
        return None

    option_id = _read_payload_value(raw_payload, "option_id", "optionId")
    if option_id == "correct_option_index":
        return None

    text = _normalize_required_string(_read_payload_value(raw_payload, "text"), default="")
    if not text:
        return None

    return Option(
        option_id=_normalize_required_string(option_id, default=f"option-{option_index + 1}"),
        text=text,
    )


def _extract_inlined_correct_option_index(raw_options: list[Any]) -> int | None:
    """Извлечь correct_option_index если модель ошибочно поместила его в массив options.

    Паттерн 1 — псевдо-опция с ключом correct_option_index:
      {"option_id": "correct_option_index", "text": "c"}

    Паттерн 2 — дублирующаяся последняя опция:
      Модель добавляет в конец копию правильного варианта с тем же option_id или текстом.
      Последняя опция отфильтровывается, а индекс первого вхождения возвращается.
    """

    option_ids = ["a", "b", "c", "d", "e"]
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        if _read_payload_value(item, "option_id", "optionId") != "correct_option_index":
            continue
        raw_text = (_read_payload_value(item, "text") or "").strip().lower()
        if raw_text in option_ids:
            return option_ids.index(raw_text)
        try:
            return int(raw_text)
        except ValueError:
            pass

    real_options = [
        item for item in raw_options
        if isinstance(item, dict) and _read_payload_value(item, "option_id", "optionId") != "correct_option_index"
    ]
    if len(real_options) < 2:
        return None
    last = real_options[-1]
    last_text = (_read_payload_value(last, "text") or "").strip().casefold()
    last_id = str(_read_payload_value(last, "option_id", "optionId") or "").strip()
    for i, option in enumerate(real_options[:-1]):
        if not isinstance(option, dict):
            continue
        option_text = (_read_payload_value(option, "text") or "").strip().casefold()
        option_id = str(_read_payload_value(option, "option_id", "optionId") or "").strip()
        if last_text and last_text == option_text:
            return i
        if last_id and last_id == option_id:
            return i
    return None


def _has_trailing_duplicate_option(raw_options: list[Any]) -> bool:
    """Проверить что последняя опция является дублём одной из предыдущих.

    Некоторые модели добавляют правильный ответ повторно в конец списка
    вместо того чтобы задать поле correct_option_index.
    """

    real_options = [
        item for item in raw_options
        if isinstance(item, dict) and _read_payload_value(item, "option_id", "optionId") != "correct_option_index"
    ]
    if len(real_options) < 2:
        return False
    last = real_options[-1]
    last_text = (_read_payload_value(last, "text") or "").strip().casefold()
    last_id = str(_read_payload_value(last, "option_id", "optionId") or "").strip()
    for option in real_options[:-1]:
        if not isinstance(option, dict):
            continue
        if last_text and last_text == (_read_payload_value(option, "text") or "").strip().casefold():
            return True
        if last_id and last_id == str(_read_payload_value(option, "option_id", "optionId") or "").strip():
            return True
    return False


def _make_true_false_options() -> tuple[Option, ...]:
    """Вернуть стандартные варианты ответа для вопроса типа true_false."""

    return (
        Option(option_id="true", text="Да"),
        Option(option_id="false", text="Нет"),
    )


def _resolve_true_false_index(raw_payload: dict[str, Any]) -> int | None:
    """Определить correct_option_index для true_false из текстового поля correct_answer.

    Модели часто возвращают correct_answer как строку 'Да'/'Нет'/'true'/'false'/'yes'/'no'.
    Индекс 0 = Да (True), индекс 1 = Нет (False).
    """

    raw = (_read_payload_value(raw_payload, "correct_answer", "correctAnswer") or "").strip().lower()
    if raw in {"да", "true", "yes", "1"}:
        return 0
    if raw in {"нет", "false", "no", "0"}:
        return 1
    return None


def _normalize_explanation(raw_payload: Any) -> Explanation | None:
    """Нормализовать необязательный payload пояснения."""

    if raw_payload is None:
        return None

    if isinstance(raw_payload, str):
        normalized_text = raw_payload.strip()
        return None if not normalized_text else Explanation(text=normalized_text)

    if isinstance(raw_payload, dict):
        normalized_text = _normalize_required_string(_read_payload_value(raw_payload, "text"), default="")
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
        left = _normalize_required_string(_read_payload_value(pair_payload, "left"), default="")
        right = _normalize_required_string(_read_payload_value(pair_payload, "right"), default="")
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


def _read_payload_value(raw_payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Прочитать значение из payload с поддержкой snake_case и camelCase ключей."""

    for key in keys:
        if key in raw_payload:
            return raw_payload[key]
    return default


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

    if "correct_option_number" in raw_payload or "correctOptionNumber" in raw_payload:
        raw_value = _read_payload_value(raw_payload, "correct_option_number", "correctOptionNumber")
        if raw_value is None:
            return None
        return _normalize_integer(raw_value, default=1, field_name=field_name) - 1
    if "correct_option_index" in raw_payload or "correctOptionIndex" in raw_payload:
        raw_value = _read_payload_value(raw_payload, "correct_option_index", "correctOptionIndex")
        if raw_value is None:
            return None
        return _normalize_integer(raw_value, default=0, field_name=field_name)
    return None
