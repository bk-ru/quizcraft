"""Разрешенные enum'ы для параметров запроса генерации."""

from __future__ import annotations

from enum import Enum


class Difficulty(str, Enum):
    """Разрешенные значения сложности для запросов генерации."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizType(str, Enum):
    """Разрешенные значения типа квиза для запросов генерации."""

    SINGLE_CHOICE = "single_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    MATCHING = "matching"


class Language(str, Enum):
    """Разрешенные языковые теги для запросов генерации."""

    RU = "ru"
    EN = "en"
