"""Lightweight groundedness helpers for matching questions."""

from __future__ import annotations

import re

from backend.app.domain.models import MatchingPair

MATCHING_GROUNDEDNESS_ERROR_MESSAGE = (
    "Вопрос на соответствие не прошёл проверку: пары должны быть явно основаны на тексте документа."
)
_SIGNIFICANT_TERM_MIN_LENGTH = 12
_WORD_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")
_SUBSCRIPT_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_PUNCTUATION_NORMALIZE = str.maketrans({"→": " ", "/": " ", "−": "-", "–": "-", "—": "-"})

_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"co2", "углекислый газ", "двуокись углерода", "диоксид углерода"}),
    frozenset({"o2", "кислород"}),
    frozenset({"атф", "atp", "аденозинтрифосфат"}),
    frozenset({"надфн", "nadph", "никотинамидадениндинуклеотидфосфат"}),
    frozenset({"сахара", "углеводы", "глюкоза"}),
    frozenset({"фотосинтез", "фотосинтетический"}),
    frozenset({"хлоропласт", "хлоропласты"}),
    frozenset({"тилакоид", "тилакоиды", "тилакоидный"}),
    frozenset({"строма", "стромы"}),
)

_SYNONYM_LOOKUP: dict[str, frozenset[str]] = {}
for _group in _SYNONYM_GROUPS:
    for _term in _group:
        _SYNONYM_LOOKUP[_term] = _group


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
    if not left_present and not right_present:
        return False

    if left_present and right_present:
        return True

    present_side = left if left_present else right
    checked_side = right if left_present else left
    if _has_absent_novel_term(checked_side, normalized_source_text, present_side):
        return False
    return True


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
        synonym_group = _SYNONYM_LOOKUP.get(term)
        if synonym_group and any(syn in normalized_source_text for syn in synonym_group):
            continue
        if present_value and term in present_value:
            continue
        return True
    return False
