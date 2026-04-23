from __future__ import annotations

import pytest

from backend.app.domain.enums import Difficulty
from backend.app.domain.enums import Language
from backend.app.domain.enums import QuizType


def test_difficulty_whitelist_contains_expected_values() -> None:
    assert {member.value for member in Difficulty} == {"easy", "medium", "hard"}


def test_quiz_type_whitelist_contains_single_choice() -> None:
    assert {member.value for member in QuizType} == {"single_choice"}


def test_language_whitelist_contains_expected_tags() -> None:
    assert {member.value for member in Language} == {"ru", "en"}


def test_difficulty_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        Difficulty("insane")


def test_language_rejects_russian_name_in_cyrillic() -> None:
    with pytest.raises(ValueError):
        Language("русский")
