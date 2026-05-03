from dataclasses import replace

import pytest

from backend.app.core.config import ConfigurationError
from backend.app.core.modes import GenerationMode, GenerationModeRegistry
from backend.app.domain.errors import BackendError, DomainValidationError, UnsupportedGenerationModeError
from backend.app.domain.models import Explanation, GenerationRequest, GenerationResult, MatchingPair, Option, Question, Quiz
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


def test_question_model_roundtrips_russian_non_choice_shapes() -> None:
    quiz = Quiz(
        quiz_id="quiz-ru",
        document_id="doc-ru",
        title="Русский квиз",
        version=1,
        last_edited_at="2026-05-03T09:00:00Z",
        questions=(
            Question(
                question_id="q-fill",
                prompt="Столица России — ____.",
                question_type="fill_blank",
                correct_answer="Москва",
                explanation=Explanation(text="Москва — столица России."),
            ),
            Question(
                question_id="q-match",
                prompt="Сопоставьте города и реки.",
                question_type="matching",
                matching_pairs=(
                    MatchingPair(left="Санкт-Петербург", right="Нева"),
                    MatchingPair(left="Казань", right="Казанка"),
                ),
            ),
        ),
    )

    restored = Quiz.from_dict(quiz.to_dict())

    assert restored.questions[0].question_type == "fill_blank"
    assert restored.questions[0].correct_answer == "Москва"
    assert restored.questions[1].question_type == "matching"
    assert restored.questions[1].matching_pairs[0].left == "Санкт-Петербург"
    assert restored.questions[1].matching_pairs[0].right == "Нева"


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
        GenerationModeRegistry.ensure_supported("hybrid_super_mode")


def test_configuration_error_inherits_from_backend_error() -> None:
    assert issubclass(ConfigurationError, BackendError)


def test_quiz_json_schema_exposes_expected_structure() -> None:
    assert QUIZ_JSON_SCHEMA["type"] == "object"
    assert QUIZ_JSON_SCHEMA["required"] == ["quiz_id", "document_id", "title", "version", "last_edited_at", "questions"]
    assert QUIZ_JSON_SCHEMA["properties"]["questions"]["type"] == "array"
    question_schema = QUIZ_JSON_SCHEMA["properties"]["questions"]["items"]
    assert question_schema["properties"]["question_type"]["enum"] == [
        "single_choice",
        "true_false",
        "fill_blank",
        "short_answer",
        "matching",
    ]
    assert question_schema["properties"]["options"]["type"] == "array"
    assert question_schema["properties"]["correct_option_index"]["oneOf"][1]["type"] == "integer"
    assert question_schema["properties"]["correct_answer"]["oneOf"][1]["type"] == "string"
    assert question_schema["properties"]["matching_pairs"]["type"] == "array"
