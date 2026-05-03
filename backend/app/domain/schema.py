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
                    "question_type",
                    "prompt",
                    "explanation",
                ],
                "properties": {
                    "question_id": {"type": "string"},
                    "question_type": {
                        "type": "string",
                        "enum": ["single_choice", "true_false", "fill_blank", "short_answer", "matching"],
                    },
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 0,
                        "items": {
                            "type": "object",
                            "required": ["option_id", "text"],
                            "properties": {
                                "option_id": {"type": "string"},
                                "text": {"type": "string"},
                            },
                        },
                    },
                    "correct_option_index": {
                        "oneOf": [
                            {"type": "null"},
                            {"type": "integer", "minimum": 0},
                        ],
                    },
                    "correct_answer": {
                        "oneOf": [
                            {"type": "null"},
                            {"type": "string"},
                        ],
                    },
                    "matching_pairs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["left", "right"],
                            "properties": {
                                "left": {"type": "string"},
                                "right": {"type": "string"},
                            },
                        },
                    },
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

QUESTION_JSON_SCHEMA = QUIZ_JSON_SCHEMA["properties"]["questions"]["items"]
