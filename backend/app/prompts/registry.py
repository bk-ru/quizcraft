"""Versioned prompt registry for supported generation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from backend.app.domain.errors import PromptResolutionError
from backend.app.domain.schema import QUESTION_JSON_SCHEMA
from backend.app.domain.schema import QUIZ_JSON_SCHEMA

DIRECT_GENERATION_PROMPT_KEY = "direct_generation"
REPAIR_GENERATION_PROMPT_KEY = "repair_generation"
SINGLE_QUESTION_REGENERATION_PROMPT_KEY = "single_question_regeneration"


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    """Resolved prompt definition with versioning and provider metadata."""

    key: str
    version: str
    schema_name: str
    schema: dict[str, Any]
    system_template: str
    user_template: str
    inference_parameters: dict[str, Any] = field(default_factory=dict)


class PromptRegistry:
    """Registry for all versioned prompt definitions used by generation flows."""

    _registry = {
        DIRECT_GENERATION_PROMPT_KEY: PromptDefinition(
            key=DIRECT_GENERATION_PROMPT_KEY,
            version="direct-v1",
            schema_name="quiz_payload",
            schema=QUIZ_JSON_SCHEMA,
            system_template=(
                "You generate quiz content strictly from the document provided by the caller. "
                "Return only JSON that matches the supplied JSON Schema. "
                "Do not rely on outside knowledge, do not invent facts, and use the requested language exactly."
            ),
            user_template=(
                "Create a quiz from the document below.\n"
                "Question count: {question_count}\n"
                "Language: {language}\n"
                "Difficulty: {difficulty}\n"
                "Quiz type: {quiz_type}\n"
                "Use only the document content.\n"
                "Document ID: {document_id}\n"
                "Document text:\n{document_text}"
            ),
            inference_parameters={"temperature": 0.2},
        ),
        REPAIR_GENERATION_PROMPT_KEY: PromptDefinition(
            key=REPAIR_GENERATION_PROMPT_KEY,
            version="repair-v1",
            schema_name="quiz_payload",
            schema=QUIZ_JSON_SCHEMA,
            system_template=(
                "You repair invalid quiz JSON. "
                "Return only corrected JSON that matches the supplied JSON Schema. "
                "Preserve valid content, remove invalid fields, and do not add explanations outside the schema."
            ),
            user_template=(
                "Repair the invalid quiz JSON below.\n"
                "Validation error: {validation_error}\n"
                "Invalid JSON:\n{invalid_json}"
            ),
            inference_parameters={"temperature": 0.0},
        ),
        SINGLE_QUESTION_REGENERATION_PROMPT_KEY: PromptDefinition(
            key=SINGLE_QUESTION_REGENERATION_PROMPT_KEY,
            version="single-question-regen-v1",
            schema_name="question_payload",
            schema=QUESTION_JSON_SCHEMA,
            system_template=(
                "You regenerate exactly one single quiz question from the supplied document and quiz context. "
                "Return only JSON that matches the supplied JSON Schema. "
                "Keep the response in the requested language, do not replace any other question, and do not invent facts."
            ),
            user_template=(
                "Regenerate the target quiz question only.\n"
                "Language: {language}\n"
                "Difficulty: {difficulty}\n"
                "Quiz type: {quiz_type}\n"
                "Additional instructions: {instructions}\n"
                "Document ID: {document_id}\n"
                "Document text:\n{document_text}\n"
                "Existing quiz JSON:\n{quiz_json}\n"
                "Target question JSON:\n{target_question_json}"
            ),
            inference_parameters={"temperature": 0.2},
        ),
    }

    @classmethod
    def resolve(cls, prompt_key: str) -> PromptDefinition:
        """Return a prompt definition or raise a controlled domain error."""

        try:
            return cls._registry[prompt_key]
        except KeyError as error:
            raise PromptResolutionError(f"prompt key was not found: {prompt_key}") from error
