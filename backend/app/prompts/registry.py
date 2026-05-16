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
RAG_GENERATION_PROMPT_KEY = "rag_generation"


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    """Resolved prompt definition with provider metadata."""

    key: str
    version: str
    schema_name: str
    schema: dict[str, Any]
    system_template: str
    user_template: str
    inference_parameters: dict[str, Any] = field(default_factory=dict)


class PromptRegistry:
    """Registry of versioned prompt definitions used by generation flows."""

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
                "Question type policy: {question_type_policy}\n"
                "Question type rules:\n{question_type_rules}\n"
                "For matching questions:\n"
                "- Create matching only when you can provide at least 4 pairs.\n"
                "- Do not use only two stages as a matching question.\n"
                "- Do not use options for matching questions.\n"
                "- Do not use symbolic answers like A/B/1/2 in matching_pairs.right.\n"
                "- Put the full answer text in matching_pairs.right.\n"
                "- Each matching pair must be explicitly supported by the document/context.\n"
                "- Do not add terms that are absent from the document/context.\n"
                "- Prefer extracting pairs from explicit document relationships: "
                "term→definition, stage→location, process→result, factor→effect, substance→role, organoid→function.\n"
                "- If matching is allowed but you cannot create 4 pairs, replace that question with another allowed type.\n"
                "Use only the document content.\n"
                "Set title to a short descriptive name for the quiz written in the requested language. "
                "Do NOT use IDs or technical strings as the title.\n"
                "Set document_id to: {document_id}\n"
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
                "Original generation settings:\n"
                "Question count: {question_count}\n"
                "Language: {language}\n"
                "Difficulty: {difficulty}\n"
                "Quiz type: {quiz_type}\n"
                "Question type policy: {question_type_policy}\n"
                "Question type rules:\n{question_type_rules}\n"
                "The repaired JSON must satisfy the original settings. Replace invalid question types with allowed ones.\n"
                "CRITICAL: You must preserve the quiz shape.\n"
                "Return exactly {question_count} questions.\n"
                "Do not remove valid questions.\n"
                "Do not merge questions.\n"
                "Do not return only the invalid question.\n"
                "Keep the same question_id values unless a question itself is invalid.\n"
                "Repair only the invalid parts.\n"
                "If only one matching question is invalid, change only that matching question.\n"
                "If validation_error says \"matching question must have at least four pairs\":\n"
                "- Find every question with question_type=\"matching\".\n"
                "- If matching_pairs has fewer than 4 items, fix that question.\n"
                "- Prefer adding missing pairs from the source document/context.\n"
                "- If the source document/context is unavailable, replace the invalid matching question with another allowed question type.\n"
                "- Never return a matching question with fewer than 4 matching_pairs.\n"
                "If a matching question uses options or A/B/1/2 values in matching_pairs.right:\n"
                "- Remove options from that matching question.\n"
                "- Replace matching_pairs.right with the full matching text.\n"
                "- Ensure every pair is supported by the source document/context.\n"
                "- Remove or replace any pair that introduces a term absent from the source document/context.\n"
                "- Never add external examples or outside knowledge.\n"
                "If validation_error says matching pairs must be grounded or explicitly based on the document:\n"
                "- Find invalid matching questions.\n"
                "- Replace only unsupported matching_pairs with pairs explicitly present in the source document/context.\n"
                "- Preserve all other questions exactly.\n"
                "- Keep total question count exactly {question_count}.\n"
                "Source document/context:\n{source_text}\n"
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
        RAG_GENERATION_PROMPT_KEY: PromptDefinition(
            key=RAG_GENERATION_PROMPT_KEY,
            version="rag-v1",
            schema_name="quiz_payload",
            schema=QUIZ_JSON_SCHEMA,
            system_template=(
                "You generate quiz content strictly from the retrieved context provided by the caller. "
                "Return only JSON that matches the supplied JSON Schema. "
                "Do not rely on outside knowledge, do not invent facts, and use the requested language exactly."
            ),
            user_template=(
                "Create a quiz from the retrieved context below.\n"
                "Question count: {question_count}\n"
                "Language: {language}\n"
                "Difficulty: {difficulty}\n"
                "Quiz type: {quiz_type}\n"
                "Question type policy: {question_type_policy}\n"
                "Question type rules:\n{question_type_rules}\n"
                "For matching questions:\n"
                "- Create matching only when you can provide at least 4 pairs.\n"
                "- Do not use only two stages as a matching question.\n"
                "- Do not use options for matching questions.\n"
                "- Do not use symbolic answers like A/B/1/2 in matching_pairs.right.\n"
                "- Put the full answer text in matching_pairs.right.\n"
                "- Each matching pair must be explicitly supported by the document/context.\n"
                "- Do not add terms that are absent from the document/context.\n"
                "- Prefer extracting pairs from explicit document relationships: "
                "term→definition, stage→location, process→result, factor→effect, substance→role, organoid→function.\n"
                "- If matching is allowed but you cannot create 4 pairs, replace that question with another allowed type.\n"
                "Use only the retrieved context.\n"
                "Set title to a short descriptive name for the quiz written in the requested language. "
                "Do NOT use IDs or technical strings as the title.\n"
                "Set document_id to: {document_id}\n"
                "Retrieved context:\n{retrieved_context}"
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
