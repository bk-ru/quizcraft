"""Lightweight groundedness helpers for matching questions."""

from __future__ import annotations

import re

from backend.app.domain.models import MatchingPair

MATCHING_GROUNDEDNESS_ERROR_MESSAGE = (
    "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
)
_SIGNIFICANT_TERM_MIN_LENGTH = 10
_WORD_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")


def normalize_grounding_text(value: str) -> str:
    """Normalize text for conservative source-grounding checks."""

    return " ".join(value.casefold().split())


def is_matching_pair_grounded(pair: MatchingPair, normalized_source_text: str) -> bool:
    """Return whether a matching pair is sufficiently supported by the source text."""

    left = normalize_grounding_text(pair.left)
    right = normalize_grounding_text(pair.right)
    if not left or not right:
        return False

    left_present = left in normalized_source_text
    right_present = right in normalized_source_text
    if not left_present and not right_present:
        return False

    return not (
        _has_absent_significant_term(left, normalized_source_text)
        or _has_absent_significant_term(right, normalized_source_text)
    )


def _has_absent_significant_term(value: str, normalized_source_text: str) -> bool:
    terms = {
        term
        for term in _WORD_PATTERN.findall(value)
        if len(term) >= _SIGNIFICANT_TERM_MIN_LENGTH and not term.isdigit()
    }
    return any(term not in normalized_source_text for term in terms)
