"""Lightweight groundedness helpers for matching questions."""

from __future__ import annotations

import re

from backend.app.domain.models import MatchingPair

MATCHING_GROUNDEDNESS_ERROR_MESSAGE = (
    "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
)
_SIGNIFICANT_TERM_MIN_LENGTH = 12
_CONTENT_TOKEN_MIN_LENGTH = 4
_MIN_TOKEN_SUPPORT_RATIO = 0.5
_WORD_PATTERN = re.compile(r"[^\W_]+")
_SUBSCRIPT_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_PUNCTUATION_NORMALIZE = str.maketrans({"→": " ", "/": " ", "−": "-", "–": "-", "—": "-"})


def normalize_grounding_text(value: str) -> str:
    """Normalize text for conservative source-grounding checks."""

    return " ".join(value.translate(_SUBSCRIPT_MAP).translate(_PUNCTUATION_NORMALIZE).casefold().split())


def is_matching_pair_grounded(pair: MatchingPair, normalized_source_text: str) -> bool:
    """Return whether a matching pair is sufficiently supported by the source text."""

    left = normalize_grounding_text(pair.left)
    right = normalize_grounding_text(pair.right)
    if not left or not right:
        return False

    left_present = left in normalized_source_text
    right_present = right in normalized_source_text
    source_tokens = frozenset(_WORD_PATTERN.findall(normalized_source_text))
    left_supported = left_present or _has_token_support(left, normalized_source_text, source_tokens)
    right_supported = right_present or _has_token_support(right, normalized_source_text, source_tokens)
    if not left_supported or not right_supported:
        return False

    if left_present and right_present:
        return True

    if _has_absent_novel_term(left, normalized_source_text, right if right_supported else None):
        return False
    if _has_absent_novel_term(right, normalized_source_text, left if left_supported else None):
        return False
    return True


def _has_token_support(
    value: str,
    normalized_source_text: str,
    source_tokens: frozenset[str],
) -> bool:
    tokens = _content_tokens(value)
    if not tokens:
        return value in normalized_source_text
    supported_count = sum(1 for token in tokens if _token_supported(token, source_tokens))
    required_count = max(1, int(len(tokens) * _MIN_TOKEN_SUPPORT_RATIO + 0.999))
    return supported_count >= required_count


def _content_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in _WORD_PATTERN.findall(value)
        if len(token) >= _CONTENT_TOKEN_MIN_LENGTH and not token.isdigit()
    )


def _token_supported(
    token: str,
    source_tokens: frozenset[str],
) -> bool:
    if token in source_tokens:
        return True
    return any(_tokens_share_stem(token, source_token) for source_token in source_tokens)


def _tokens_share_stem(token: str, source_token: str) -> bool:
    common_length = 0
    for left_char, right_char in zip(token, source_token):
        if left_char != right_char:
            break
        common_length += 1
    required_length = min(5, len(token), len(source_token))
    required_length = max(4, required_length)
    return common_length >= required_length


def _has_absent_novel_term(
    checked_value: str,
    normalized_source_text: str,
    present_value: str | None = None,
) -> bool:
    terms = {
        term
        for term in _WORD_PATTERN.findall(checked_value)
        if len(term) >= _SIGNIFICANT_TERM_MIN_LENGTH and not term.isdigit()
    }
    for term in terms:
        if term in normalized_source_text:
            continue
        if present_value and term in present_value:
            continue
        return True
    return False
