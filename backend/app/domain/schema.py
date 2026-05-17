"""JSON Schema artifacts generated from Pydantic models for LLM structured generation."""

from __future__ import annotations

from typing import Any

from backend.app.domain.pydantic_models import get_quiz_json_schema as _get_quiz_schema


def _build_question_schema() -> dict[str, Any]:
    """Extract question schema from full quiz schema."""
    full = _get_quiz_schema()
    return full["properties"]["questions"]["items"]


# Lazily-evaluated schemas for backward compatibility
QUIZ_JSON_SCHEMA: dict[str, Any] = _get_quiz_schema()
QUESTION_JSON_SCHEMA: dict[str, Any] = _build_question_schema()
