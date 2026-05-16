"""Fallback helpers for invalid matching questions."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import MatchingPair
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.validation import MATCHING_SYMBOLIC_RIGHT_VALUES
from backend.app.generation.matching_grounding import is_matching_pair_grounded
from backend.app.generation.matching_grounding import MATCHING_GROUNDEDNESS_ERROR_MESSAGE
from backend.app.generation.matching_grounding import normalize_grounding_text
from backend.app.generation.question_types import allowed_question_types

MIN_MATCHING_PAIRS = 4
MATCHING_PAIR_VALIDATION_MESSAGE = "matching question must have at least four pairs"
REPAIR_SOURCE_TEXT_MAX_CHARS = 2_500

_MATCHING_ERROR_SUBSTRINGS = (
    MATCHING_GROUNDEDNESS_ERROR_MESSAGE,
    MATCHING_PAIR_VALIDATION_MESSAGE,
    "matching question must not include options",
    "matching pair right must contain full text, not an option id",
    "matching question correct answer must be empty",
    "matching question correct option index must be empty",
)


def is_matching_pair_count_error(error: Exception) -> bool:
    return MATCHING_PAIR_VALIDATION_MESSAGE in str(getattr(error, "message", str(error)))


def is_matching_error(error: Exception) -> bool:
    """Вернуть True, если ошибка связана с matching-вопросом."""
    message = str(getattr(error, "message", str(error)))
    return any(sub in message for sub in _MATCHING_ERROR_SUBSTRINGS)


def build_matching_pair_count_error(response_content: dict[str, Any]) -> GenerationQualityError:
    pair_count = _first_invalid_matching_pair_count(response_content)
    if pair_count is None:
        return GenerationQualityError(
            "Вопрос на соответствие не прошёл проверку: модель вернула меньше 4 пар."
        )
    return GenerationQualityError(
        f"Вопрос на соответствие не прошёл проверку: модель вернула {pair_count} пары, нужно минимум 4."
    )


def fallback_invalid_matching_questions(
    quiz: Quiz,
    generation_request: GenerationRequest,
    *,
    source_text: str | None = None,
) -> Quiz | None:
    """Convert invalid matching questions to short_answer when that is explicitly allowed."""

    allowed_types = allowed_question_types(generation_request)
    if "short_answer" not in allowed_types or allowed_types == ("matching",):
        return None

    normalized_source_text = normalize_grounding_text(source_text or "")
    repaired_questions: list[Question] = []
    changed = False
    for question in quiz.questions:
        if question.question_type != "matching":
            repaired_questions.append(question)
            continue
        if not _matching_question_needs_fallback(question, normalized_source_text):
            repaired_questions.append(question)
            continue
        repaired_questions.append(
            _matching_question_to_short_answer(
                question,
                generation_request,
                normalized_source_text=normalized_source_text,
            )
        )
        changed = True

    if not changed:
        return None
    return replace(quiz, questions=tuple(repaired_questions))


def prepare_repair_source_text(source_text: str) -> str:
    normalized = source_text.strip()
    if len(normalized) <= REPAIR_SOURCE_TEXT_MAX_CHARS:
        return normalized
    return normalized[:REPAIR_SOURCE_TEXT_MAX_CHARS].rstrip()


def build_repair_source_excerpt(
    source_text: str,
    invalid_quiz_or_question: dict[str, Any],
    max_chars: int = REPAIR_SOURCE_TEXT_MAX_CHARS,
) -> str:
    """Выдержка из source_text по терминам из невалидного matching-вопроса."""
    terms = _extract_matching_terms(invalid_quiz_or_question)
    if not terms:
        return source_text.strip()[:max_chars].rstrip()
    paragraphs = [p.strip() for p in source_text.split("\n\n") if p.strip()]
    relevant: list[str] = []
    total_len = 0
    for para in paragraphs:
        para_lower = para.casefold()
        if any(t.casefold() in para_lower for t in terms):
            if total_len + len(para) + 2 <= max_chars:
                relevant.append(para)
                total_len += len(para) + 2
    if not relevant:
        return source_text.strip()[:max_chars].rstrip()
    return "\n\n".join(relevant)


def _extract_matching_terms(payload: dict[str, Any]) -> list[str]:
    """Собрать термины из matching_pairs невалидного вопроса."""
    terms: list[str] = []
    questions = payload.get("questions")
    if not isinstance(questions, list):
        return terms
    for question in questions:
        if not isinstance(question, dict):
            continue
        if question.get("question_type") != "matching":
            continue
        pairs = question.get("matching_pairs")
        if not isinstance(pairs, list):
            continue
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            for key in ("left", "right"):
                value = pair.get(key, "")
                if isinstance(value, str) and value.strip():
                    terms.append(value.strip())
    return terms


def estimate_repair_prompt_chars(
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
) -> int:
    """Приблизительная оценка размера repair-запроса в символах."""
    import json as _json
    return (
        len(system_prompt)
        + len(user_prompt)
        + len(_json.dumps(schema, ensure_ascii=False))
    )


def _matching_question_needs_fallback(question: Question, normalized_source_text: str) -> bool:
    if question.options:
        return True
    if question.correct_option_index is not None or question.correct_answer is not None:
        return True
    if len(question.matching_pairs) < MIN_MATCHING_PAIRS:
        return True
    if any(_is_symbolic_right_value(pair.right) for pair in question.matching_pairs):
        return True
    if normalized_source_text:
        return any(not is_matching_pair_grounded(pair, normalized_source_text) for pair in question.matching_pairs)
    return False


def _matching_question_to_short_answer(
    question: Question,
    generation_request: GenerationRequest,
    *,
    normalized_source_text: str,
) -> Question:
    grounded_pairs = _grounded_matching_pairs(question, normalized_source_text)
    answer = _short_answer_value(grounded_pairs, generation_request)
    prompt = _short_answer_prompt(grounded_pairs, generation_request)
    return replace(
        question,
        question_type="short_answer",
        prompt=prompt,
        options=(),
        correct_option_index=None,
        correct_answer=answer,
        matching_pairs=(),
    )


def _grounded_matching_pairs(question: Question, normalized_source_text: str) -> tuple[MatchingPair, ...]:
    option_text_by_id = {option.option_id.strip().casefold(): option.text for option in question.options}
    grounded_pairs: list[MatchingPair] = []
    for pair in question.matching_pairs:
        repaired_pair = MatchingPair(
            left=pair.left,
            right=option_text_by_id.get(pair.right.strip().casefold(), pair.right),
        )
        if not repaired_pair.left.strip() or not repaired_pair.right.strip():
            continue
        if _is_symbolic_right_value(repaired_pair.right):
            continue
        if normalized_source_text and not is_matching_pair_grounded(repaired_pair, normalized_source_text):
            continue
        grounded_pairs.append(repaired_pair)
    return tuple(grounded_pairs)


def _short_answer_value(grounded_pairs: tuple[MatchingPair, ...], generation_request: GenerationRequest) -> str:
    if grounded_pairs:
        return "; ".join(f"{pair.left} — {pair.right}" for pair in grounded_pairs)
    if generation_request.language.strip().casefold().startswith("ru"):
        return "Ответ должен опираться только на явно описанные в тексте соответствия."
    return "The answer must use only relationships explicitly described in the source text."


def _short_answer_prompt(grounded_pairs: tuple[MatchingPair, ...], generation_request: GenerationRequest) -> str:
    language = generation_request.language.strip().casefold()
    if language.startswith("ru"):
        if 2 <= len(grounded_pairs) <= 3:
            concepts = ", ".join(pair.left for pair in grounded_pairs)
            return f"Кратко сравните связанные понятия из текста: {concepts}."
        return "Какие соответствия между понятиями описаны в тексте?"
    if 2 <= len(grounded_pairs) <= 3:
        concepts = ", ".join(pair.left for pair in grounded_pairs)
        return f"Briefly compare the related concepts from the text: {concepts}."
    return "Which relationships between concepts are described in the text?"


def _is_symbolic_right_value(value: str) -> bool:
    return value.strip().casefold() in MATCHING_SYMBOLIC_RIGHT_VALUES


def _first_invalid_matching_pair_count(response_content: dict[str, Any]) -> int | None:
    questions = response_content.get("questions")
    if not isinstance(questions, list):
        return None
    for question in questions:
        if not isinstance(question, dict):
            continue
        if question.get("question_type") != "matching":
            continue
        matching_pairs = question.get("matching_pairs")
        pair_count = len(matching_pairs) if isinstance(matching_pairs, list) else 0
        if pair_count < MIN_MATCHING_PAIRS:
            return pair_count
    return None
