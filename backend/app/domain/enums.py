"""Whitelisted enums for generation-request parameters."""

from __future__ import annotations

from enum import Enum


class Difficulty(str, Enum):
    """Allowed difficulty values for generation requests."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizType(str, Enum):
    """Allowed quiz-type values for generation requests."""

    SINGLE_CHOICE = "single_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    MATCHING = "matching"


class Language(str, Enum):
    """Allowed language tags for generation requests."""

    RU = "ru"
    EN = "en"
