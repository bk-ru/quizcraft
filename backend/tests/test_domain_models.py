from dataclasses import replace

import pytest

from backend.app.core.config import ConfigurationError
from backend.app.core.modes import GenerationMode, GenerationModeRegistry
from backend.app.domain.errors import BackendError, DomainValidationError, UnsupportedGenerationModeError
from backend.app.domain.models import Explanation, GenerationRequest, GenerationResult, Option, Question, Quiz
from backend.app.domain.schema import QUIZ_JSON_SCHEMA
from backend.app.domain.validation import validate_quiz


def build_valid_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-1",
        document_id="doc-1",
        title="Sample quiz",
        version=1,
        last_edited_at="2026-04-17T16:00:00Z",
        questions=(
            Question(
                question_id="question-1",
                prompt="What is the capital of France?",
                options=(
                    Option(option_id="option-1", text="Paris"),
                    Option(option_id="option-2", text="Rome"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Paris is the capital of France."),
            ),
        ),
    )


def test_domain_models_capture_generation_metadata() -> None:
    quiz = build_valid_quiz()
    request = GenerationRequest(
        question_count=5,
        language="ru",
        difficulty="medium",
        quiz_type="single_choice",
        generation_mode=GenerationMode.DIRECT,
    )
    result = GenerationResult(
        quiz=quiz,
        request=request,
        model_name="local-model",
        prompt_version="v1",
    )

    assert result.quiz.title == "Sample quiz"
    assert result.request.question_count == 5
    assert result.model_name == "local-model"
    assert result.prompt_version == "v1"


def test_validate_quiz_accepts_well_formed_quiz() -> None:
    validate_quiz(build_valid_quiz())


def test_validate_quiz_rejects_empty_question_prompt() -> None:
    quiz = build_valid_quiz()
    broken_question = replace(quiz.questions[0], prompt="")
    broken_quiz = replace(quiz, questions=(broken_question,))

    with pytest.raises(DomainValidationError, match="question prompt"):
        validate_quiz(broken_quiz)


def test_validate_quiz_rejects_duplicate_option_text() -> None:
    quiz = build_valid_quiz()
    duplicate_question = replace(
        quiz.questions[0],
        options=(
            Option(option_id="option-1", text="Paris"),
            Option(option_id="option-2", text=" Paris "),
        ),
    )
    broken_quiz = replace(quiz, questions=(duplicate_question,))

    with pytest.raises(DomainValidationError, match="duplicate"):
        validate_quiz(broken_quiz)


def test_generation_mode_registry_supports_direct_mode() -> None:
    assert GenerationModeRegistry.ensure_supported("direct") is GenerationMode.DIRECT


def test_generation_mode_registry_rejects_unknown_mode() -> None:
    with pytest.raises(UnsupportedGenerationModeError, match="unsupported"):
        GenerationModeRegistry.ensure_supported("rag")


def test_configuration_error_inherits_from_backend_error() -> None:
    assert issubclass(ConfigurationError, BackendError)


def test_quiz_json_schema_exposes_expected_structure() -> None:
    assert QUIZ_JSON_SCHEMA["type"] == "object"
    assert QUIZ_JSON_SCHEMA["required"] == ["quiz_id", "document_id", "title", "version", "last_edited_at", "questions"]
    assert QUIZ_JSON_SCHEMA["properties"]["questions"]["type"] == "array"
    question_schema = QUIZ_JSON_SCHEMA["properties"]["questions"]["items"]
    assert question_schema["properties"]["options"]["type"] == "array"
    assert question_schema["properties"]["correct_option_index"]["type"] == "integer"
