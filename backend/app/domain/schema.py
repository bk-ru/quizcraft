"""Compact JSON Schema artifacts for LLM structured generation."""

from __future__ import annotations

from typing import Any

_EXPLANATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["text"],
    "properties": {
        "text": {"type": "string", "minLength": 1},
    },
}

_OPTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["optionId", "text"],
    "properties": {
        "optionId": {"type": "string", "minLength": 1},
        "text": {"type": "string", "minLength": 1},
    },
}

_MATCHING_PAIR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["left", "right"],
    "properties": {
        "left": {"type": "string", "minLength": 1},
        "right": {"type": "string", "minLength": 1},
    },
}

QUESTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["questionId", "questionType", "prompt"],
    "properties": {
        "questionId": {"type": "string", "minLength": 1},
        "questionType": {
            "type": "string",
            "enum": ["single_choice", "true_false", "fill_blank", "short_answer", "matching"],
        },
        "prompt": {"type": "string", "minLength": 1},
        "options": {"type": "array", "items": _OPTION_SCHEMA},
        "correctOptionIndex": {"oneOf": [{"type": "null"}, {"type": "integer", "minimum": 0}]},
        "correctAnswer": {"oneOf": [{"type": "null"}, {"type": "string", "minLength": 1}]},
        "matchingPairs": {
            "type": "array",
            "minItems": 4,
            "items": _MATCHING_PAIR_SCHEMA,
        },
        "explanation": {"oneOf": [{"type": "null"}, _EXPLANATION_SCHEMA]},
    },
}

QUIZ_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quizId", "documentId", "title", "version", "lastEditedAt", "questions"],
    "properties": {
        "quizId": {"type": "string", "minLength": 1},
        "documentId": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "version": {"type": "integer", "minimum": 1},
        "lastEditedAt": {"type": "string", "minLength": 1},
        "questions": {
            "type": "array",
            "minItems": 1,
            "items": QUESTION_JSON_SCHEMA,
        },
    },
}
