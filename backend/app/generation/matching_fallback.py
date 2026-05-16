"""Fallback helpers for invalid matching questions."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.app.domain.errors import GenerationQualityError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.generation.question_types import allowed_question_types

MIN_MATCHING_PAIRS = 4
MATCHING_PAIR_VALIDATION_MESSAGE = "matching question must have at least four pairs"
REPAIR_SOURCE_TEXT_MAX_CHARS = 12_000


def is_matching_pair_count_error(error: Exception) -> bool:
    return MATCHING_PAIR_VALIDATION_MESSAGE in str(getattr(error, "message", str(error)))


def build_matching_pair_count_error(response_content: dict[str, Any]) -> GenerationQualityError:
    pair_count = _first_invalid_matching_pair_count(response_content)
    if pair_count is None:
        return GenerationQualityError(
            "Вопрос на соответствие не прошёл проверку: модель вернула меньше 4 пар."
        )
    return GenerationQualityError(
        f"Вопрос на соответствие не прошёл проверку: модель вернула {pair_count} пары, нужно минимум 4."
    )


def fallback_invalid_matching_questions(quiz: Quiz, generation_request: GenerationRequest) -> Quiz | None:
    """Convert invalid matching questions to short_answer when that is explicitly allowed."""

    allowed_types = allowed_question_types(generation_request)
    if "short_answer" not in allowed_types or allowed_types == ("matching",):
        return None

    repaired_questions: list[Question] = []
    changed = False
    for question in quiz.questions:
        if question.question_type != "matching" or len(question.matching_pairs) >= MIN_MATCHING_PAIRS:
            repaired_questions.append(question)
            continue
        if not question.matching_pairs:
            return None
        repaired_questions.append(_matching_question_to_short_answer(question, generation_request))
        changed = True

    if not changed:
        return None
    return replace(quiz, questions=tuple(repaired_questions))


def prepare_repair_source_text(source_text: str) -> str:
    normalized = source_text.strip()
    if len(normalized) <= REPAIR_SOURCE_TEXT_MAX_CHARS:
        return normalized
    return normalized[:REPAIR_SOURCE_TEXT_MAX_CHARS].rstrip()


def _matching_question_to_short_answer(question: Question, generation_request: GenerationRequest) -> Question:
    answer = "; ".join(f"{pair.left} — {pair.right}" for pair in question.matching_pairs)
    prompt = _short_answer_prompt(question, generation_request)
    return replace(
        question,
        question_type="short_answer",
        prompt=prompt,
        options=(),
        correct_option_index=None,
        correct_answer=answer,
        matching_pairs=(),
    )


def _short_answer_prompt(question: Question, generation_request: GenerationRequest) -> str:
    language = generation_request.language.strip().casefold()
    if language.startswith("ru"):
        return f"Кратко опишите соответствия из документа: {question.prompt}"
    return f"Briefly describe the relationships from the document: {question.prompt}"


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
