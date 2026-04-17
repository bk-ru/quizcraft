"""JSON Schema artifacts for persisted domain payloads."""

from __future__ import annotations

QUIZ_JSON_SCHEMA = {
    "type": "object",
    "required": [
        "quiz_id",
        "document_id",
        "title",
        "version",
        "last_edited_at",
        "questions",
    ],
    "properties": {
        "quiz_id": {"type": "string"},
        "document_id": {"type": "string"},
        "title": {"type": "string"},
        "version": {"type": "integer", "minimum": 1},
        "last_edited_at": {"type": "string", "format": "date-time"},
        "questions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "question_id",
                    "prompt",
                    "options",
                    "correct_option_index",
                    "explanation",
                ],
                "properties": {
                    "question_id": {"type": "string"},
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "required": ["option_id", "text"],
                            "properties": {
                                "option_id": {"type": "string"},
                                "text": {"type": "string"},
                            },
                        },
                    },
                    "correct_option_index": {"type": "integer", "minimum": 0},
                    "explanation": {
                        "oneOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "required": ["text"],
                                "properties": {"text": {"type": "string"}},
                            },
                        ],
                    },
                },
            },
        },
    },
}
