import pytest

from backend.app.core.modes import GenerationMode
from backend.app.core.modes import GenerationModeRegistry
from backend.app.domain.errors import PromptResolutionError
from backend.app.prompts.registry import RAG_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptRegistry


def test_generation_mode_registry_resolves_rag_mode() -> None:
    assert GenerationModeRegistry.ensure_supported("rag") is GenerationMode.RAG


def test_generation_mode_registry_resolves_uppercase_rag() -> None:
    assert GenerationModeRegistry.ensure_supported("RAG") is GenerationMode.RAG


def test_rag_prompt_definition_uses_quiz_payload_schema() -> None:
    prompt = PromptRegistry.resolve(RAG_GENERATION_PROMPT_KEY)

    assert prompt.key == RAG_GENERATION_PROMPT_KEY
    assert prompt.version == "rag-v1"
    assert prompt.schema_name == "quiz_payload"
    assert "questions" in prompt.schema["properties"]


def test_rag_prompt_user_template_references_retrieved_context_and_request_fields() -> None:
    prompt = PromptRegistry.resolve(RAG_GENERATION_PROMPT_KEY)

    assert "{retrieved_context}" in prompt.user_template
    assert "{question_count}" in prompt.user_template
    assert "{language}" in prompt.user_template
    assert "{difficulty}" in prompt.user_template
    assert "{quiz_type}" in prompt.user_template
    assert "{document_id}" in prompt.user_template
    assert "{document_text}" not in prompt.user_template


def test_rag_prompt_user_template_renders_cyrillic_context() -> None:
    prompt = PromptRegistry.resolve(RAG_GENERATION_PROMPT_KEY)

    rendered = prompt.user_template.format(
        question_count=3,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        document_id="doc-ru",
        retrieved_context="Москва — столица России. Население 13 миллионов.",
    )

    assert "Москва" in rendered
    assert "столица России" in rendered
    assert "doc-ru" in rendered


def test_rag_prompt_inference_parameters_keep_low_temperature() -> None:
    prompt = PromptRegistry.resolve(RAG_GENERATION_PROMPT_KEY)

    assert prompt.inference_parameters == {"temperature": 0.2}


def test_prompt_registry_still_rejects_unknown_keys() -> None:
    with pytest.raises(PromptResolutionError, match="prompt key"):
        PromptRegistry.resolve("not_a_real_prompt")
