import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.schema import QUIZ_JSON_SCHEMA
from backend.app.generation.request_builder import DirectGenerationRequestBuilder
from backend.app.prompts.registry import DIRECT_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import PromptRegistry


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=42,
        normalized_text="First fact.\n\nSecond fact.",
        metadata={"text_length": 25},
    )


def build_generation_request() -> GenerationRequest:
    return GenerationRequest(
        question_count=5,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )


def test_request_builder_creates_structured_provider_request_for_direct_mode() -> None:
    builder = DirectGenerationRequestBuilder(prompt_registry=PromptRegistry)

    provider_request = builder.build(
        document=build_document(),
        generation_request=build_generation_request(),
    )

    assert provider_request.schema_name == "quiz_payload"
    assert provider_request.schema == QUIZ_JSON_SCHEMA
    assert provider_request.inference_parameters == {"temperature": 0.2}
    assert provider_request.model_name is None
    assert "JSON Schema" in provider_request.system_prompt
    assert "strictly from the document" in provider_request.system_prompt
    assert "First fact.\n\nSecond fact." in provider_request.user_prompt
    assert "Question count: 5" in provider_request.user_prompt
    assert "Language: ru" in provider_request.user_prompt
    assert "Difficulty: medium" in provider_request.user_prompt
    assert "Quiz type: single_choice" in provider_request.user_prompt


def test_request_builder_rejects_unsupported_generation_mode() -> None:
    builder = DirectGenerationRequestBuilder(prompt_registry=PromptRegistry)
    unsupported_request = GenerationRequest(
        question_count=5,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode="rag",  # type: ignore[arg-type]
    )

    with pytest.raises(UnsupportedGenerationModeError, match="rag"):
        builder.build(
            document=build_document(),
            generation_request=unsupported_request,
        )


def test_request_builder_uses_direct_generation_prompt_key() -> None:
    builder = DirectGenerationRequestBuilder(prompt_registry=PromptRegistry)

    resolved_key = builder.resolve_prompt_key(build_generation_request())

    assert resolved_key == DIRECT_GENERATION_PROMPT_KEY


def test_request_builder_preserves_russian_document_text_and_language() -> None:
    builder = DirectGenerationRequestBuilder(prompt_registry=PromptRegistry)
    document = DocumentRecord(
        document_id="doc-ru-1",
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=64,
        normalized_text="Первый факт.\n\nВторой факт.",
        metadata={"text_length": 26},
    )
    generation_request = GenerationRequest(
        question_count=3,
        language="русский",
        difficulty="средний",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )

    provider_request = builder.build(document=document, generation_request=generation_request)

    assert "Первый факт.\n\nВторой факт." in provider_request.user_prompt
    assert "Language: русский" in provider_request.user_prompt
    assert "Difficulty: средний" in provider_request.user_prompt
