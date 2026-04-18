import pytest

from backend.app.domain.errors import PromptResolutionError
from backend.app.prompts.registry import DIRECT_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptRegistry


def test_prompt_registry_resolves_versioned_direct_generation_prompt() -> None:
    prompt = PromptRegistry.resolve(DIRECT_GENERATION_PROMPT_KEY)

    assert prompt.key == DIRECT_GENERATION_PROMPT_KEY
    assert prompt.version == "direct-v1"
    assert prompt.schema_name == "quiz_payload"
    assert prompt.inference_parameters == {"temperature": 0.2}
    assert "JSON Schema" in prompt.system_template
    assert "strictly from the document" in prompt.system_template
    assert "{document_text}" in prompt.user_template
    assert "{question_count}" in prompt.user_template


def test_prompt_registry_raises_controlled_error_for_unknown_prompt_key() -> None:
    with pytest.raises(PromptResolutionError, match="missing_prompt"):
        PromptRegistry.resolve("missing_prompt")
