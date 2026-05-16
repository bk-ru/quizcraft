"""Fallback helpers for invalid matching questions."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class FallbackAction:
    """Metadata about what fallback did to a single matching question."""

    action: str
    original_pair_count: int
    grounded_pair_count: int
    removed_pair_count: int
    final_question_type: str


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
) -> tuple[Quiz, tuple[FallbackAction, ...]] | None:
    """Try to clean matching questions first; convert to short_answer only when necessary.

    Returns ``(cleaned_quiz, actions)`` or ``None`` when nothing changed.
    """

    normalized_source_text = normalize_grounding_text(source_text or "")
    repaired_questions: list[Question] = []
    actions: list[FallbackAction] = []
    changed = False
    for question in quiz.questions:
        if question.question_type != "matching":
            repaired_questions.append(question)
            continue
        if not _matching_question_needs_fallback(question, normalized_source_text):
            repaired_questions.append(question)
            continue
        cleaned, action = _apply_matching_fallback(
            question,
            generation_request,
            normalized_source_text=normalized_source_text,
        )
        repaired_questions.append(cleaned)
        actions.append(action)
        if cleaned is not question:
            changed = True

    if not changed:
        return None
    return replace(quiz, questions=tuple(repaired_questions)), tuple(actions)


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


def _apply_matching_fallback(
    question: Question,
    generation_request: GenerationRequest,
    *,
    normalized_source_text: str,
) -> tuple[Question, FallbackAction]:
    """Multi-step fallback: clean matching → keep if 4+ pairs → convert otherwise."""

    allowed_types = allowed_question_types(generation_request)
    can_convert_to_short_answer = "short_answer" in allowed_types and allowed_types != ("matching",)
    original_pair_count = len(question.matching_pairs)
    cleaned_pairs = _clean_matching_pairs(question, normalized_source_text)
    grounded_count = len(cleaned_pairs)
    removed_count = original_pair_count - grounded_count

    if grounded_count >= MIN_MATCHING_PAIRS:
        cleaned_question = replace(
            question,
            question_type="matching",
            options=(),
            correct_option_index=None,
            correct_answer=None,
            matching_pairs=cleaned_pairs,
        )
        return cleaned_question, FallbackAction(
            action="cleaned_matching",
            original_pair_count=original_pair_count,
            grounded_pair_count=grounded_count,
            removed_pair_count=removed_count,
            final_question_type="matching",
        )

    if not can_convert_to_short_answer:
        return question, FallbackAction(
            action="failed",
            original_pair_count=original_pair_count,
            grounded_pair_count=grounded_count,
            removed_pair_count=removed_count,
            final_question_type="matching",
        )

    if grounded_count >= 2:
        converted = _matching_to_short_answer_multi_pair(
            cleaned_pairs, generation_request
        )
        return converted, FallbackAction(
            action="converted_to_short_answer",
            original_pair_count=original_pair_count,
            grounded_pair_count=grounded_count,
            removed_pair_count=removed_count,
            final_question_type="short_answer",
        )

    if grounded_count == 1:
        converted = _matching_to_short_answer_single_pair(
            cleaned_pairs[0], generation_request
        )
        return converted, FallbackAction(
            action="single_pair_short_answer",
            original_pair_count=original_pair_count,
            grounded_pair_count=grounded_count,
            removed_pair_count=removed_count,
            final_question_type="short_answer",
        )

    converted = _matching_to_short_answer_no_pairs(question, generation_request)
    return converted, FallbackAction(
        action="failed",
        original_pair_count=original_pair_count,
        grounded_pair_count=0,
        removed_pair_count=original_pair_count,
        final_question_type="short_answer",
    )


def _clean_matching_pairs(
    question: Question, normalized_source_text: str
) -> tuple[MatchingPair, ...]:
    """Remove ungrounded pairs, resolve symbolic right values, strip invalid entries."""

    option_text_by_id = {
        option.option_id.strip().casefold(): option.text
        for option in question.options
    }
    grounded_pairs: list[MatchingPair] = []
    for pair in question.matching_pairs:
        resolved_right = option_text_by_id.get(
            pair.right.strip().casefold(), pair.right
        )
        repaired_pair = MatchingPair(left=pair.left, right=resolved_right)
        if not repaired_pair.left.strip() or not repaired_pair.right.strip():
            continue
        if _is_symbolic_right_value(repaired_pair.right):
            continue
        if normalized_source_text and not is_matching_pair_grounded(
            repaired_pair, normalized_source_text
        ):
            continue
        grounded_pairs.append(repaired_pair)
    return tuple(grounded_pairs)


def _matching_to_short_answer_multi_pair(
    grounded_pairs: tuple[MatchingPair, ...],
    generation_request: GenerationRequest,
) -> Question:
    """Convert 2-3 grounded pairs to a natural short_answer question."""

    language = generation_request.language.strip().casefold()
    prompt = _multi_pair_prompt(grounded_pairs, language)
    answer = _multi_pair_answer(grounded_pairs)
    return Question(
        question_id="q-fallback",
        prompt=prompt,
        options=(),
        correct_option_index=None,
        explanation=None,
        question_type="short_answer",
        correct_answer=answer,
        matching_pairs=(),
    )


def _matching_to_short_answer_single_pair(
    pair: MatchingPair,
    generation_request: GenerationRequest,
) -> Question:
    """Convert 1 grounded pair to a specific short_answer question."""

    language = generation_request.language.strip().casefold()
    prompt = _single_pair_prompt(pair, language)
    answer = pair.right
    return Question(
        question_id="q-fallback",
        prompt=prompt,
        options=(),
        correct_option_index=None,
        explanation=None,
        question_type="short_answer",
        correct_answer=answer,
        matching_pairs=(),
    )


def _matching_to_short_answer_no_pairs(
    original_question: Question,
    generation_request: GenerationRequest,
) -> Question:
    """Convert a matching question with 0 grounded pairs to a generic short_answer."""

    language = generation_request.language.strip().casefold()
    if language.startswith("ru"):
        prompt = "Какие соответствия между понятиями описаны в тексте?"
        answer = "Ответ должен опираться только на явно описанные в тексте соответствия."
    else:
        prompt = "Which relationships between concepts are described in the text?"
        answer = "The answer must use only relationships explicitly described in the source text."
    return Question(
        question_id=original_question.question_id,
        prompt=prompt,
        options=(),
        correct_option_index=None,
        explanation=original_question.explanation,
        question_type="short_answer",
        correct_answer=answer,
        matching_pairs=(),
    )


def _multi_pair_prompt(
    grounded_pairs: tuple[MatchingPair, ...], language: str
) -> str:
    """Natural prompt for 2-3 grounded matching pairs."""

    left_terms = [pair.left for pair in grounded_pairs]
    if language.startswith("ru"):
        stage_terms = [t for t in left_terms if "стадия" in t.casefold()]
        if stage_terms and len(stage_terms) == len(grounded_pairs):
            concepts_str = ", ".join(left_terms)
            return f"Какие характеристики указаны в тексте для: {concepts_str}?"
        if len(grounded_pairs) >= 2:
            concepts_str = ", ".join(left_terms)
            return f"Какие соответствия между этими понятиями описаны в тексте: {concepts_str}?"
        return "Какие соответствия между понятиями описаны в тексте?"
    stage_terms = [t for t in left_terms if "stage" in t.casefold()]
    if stage_terms and len(stage_terms) == len(grounded_pairs):
        concepts_str = ", ".join(left_terms)
        return f"Which characteristics are described in the text for: {concepts_str}?"
    if len(grounded_pairs) >= 2:
        concepts_str = ", ".join(left_terms)
        return f"Which relationships between these concepts are described in the text: {concepts_str}?"
    return "Which relationships between concepts are described in the text?"


def _multi_pair_answer(grounded_pairs: tuple[MatchingPair, ...]) -> str:
    """Natural answer string for 2-3 grounded pairs."""

    return "; ".join(f"{pair.left} — {pair.right}" for pair in grounded_pairs)


def _single_pair_prompt(pair: MatchingPair, language: str) -> str:
    """Specific prompt for a single grounded matching pair."""

    left = pair.left.strip()
    right = pair.right.strip()
    if language.startswith("ru"):
        if "стадия" in left.casefold():
            return f"Что в тексте сказано о {left.lower()}?"
        if len(right) < len(left) or _looks_like_term(left):
            return f"Что в тексте связано с понятием «{left}»?"
        return f"Какое соответствие для понятия «{left}» указано в тексте?"
    if "stage" in left.casefold():
        return f"What happens during the {left.lower()}?"
    if len(right) < len(left) or _looks_like_term(left):
        return f"What is associated with the concept «{left}» in the text?"
    return f"What correspondence for the concept «{left}» is indicated in the text?"


def _looks_like_term(text: str) -> bool:
    """Heuristic: text looks like a named term (capitalized, not a full sentence)."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped[0].isupper() and "." not in stripped and "?" not in stripped:
        return True
    return False


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
