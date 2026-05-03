from __future__ import annotations

import importlib

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.core.modes import GenerationModeRegistry
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import Explanation
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import Option
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.generation import request_builder
from backend.app.prompts.registry import PromptRegistry
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.quizzes import FileSystemQuizRepository


class RecordingProvider:
    """Provider test double for targeted regeneration orchestration."""

    def __init__(
        self,
        responses: list[StructuredGenerationResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._error = error
        self.requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        raise AssertionError("healthcheck should not be called in targeted regeneration tests")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        if not self._responses:
            raise AssertionError("provider was called more times than expected")
        return self._responses.pop(0)

    def embed(self, request):
        raise AssertionError("embed should not be called in targeted regeneration tests")


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-ru",
        filename="lecture.txt",
        media_type="text/plain",
        file_size_bytes=96,
        normalized_text="Петр I основал Санкт-Петербург. Через город протекает Нева.",
        metadata={"text_length": 62},
    )


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-ru",
        document_id="doc-ru",
        title="Квиз по истории России",
        version=0,
        last_edited_at="",
        questions=(
            Question(
                question_id="q-1",
                prompt="Кто основал Санкт-Петербург?",
                options=(
                    Option(option_id="opt-1", text="Петр I"),
                    Option(option_id="opt-2", text="Иван IV"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Санкт-Петербург был основан Петром I."),
            ),
            Question(
                question_id="q-2",
                prompt="Какая река протекает через Санкт-Петербург?",
                options=(
                    Option(option_id="opt-1", text="Нева"),
                    Option(option_id="opt-2", text="Волга"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Через Санкт-Петербург протекает Нева."),
            ),
        ),
    )


def build_generation_request(**overrides: object) -> GenerationRequest:
    values: dict[str, object] = {
        "question_count": 1,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": GenerationMode.SINGLE_QUESTION_REGEN,
        "model_name": "strict-model",
        "profile_name": "strict",
        "inference_parameters": {"temperature": 0.0},
    }
    values.update(overrides)
    return GenerationRequest(**values)


def build_question_response(**overrides: object) -> StructuredGenerationResponse:
    content: dict[str, object] = {
        "question_id": "provider-q",
        "prompt": "Почему Нева важна для Санкт-Петербурга?",
        "options": [
            {"option_id": "opt-1", "text": "Она протекает через город"},
            {"option_id": "opt-2", "text": "Она находится в Сибири"},
        ],
        "correct_option_index": 0,
        "explanation": {"text": "Нева протекает через Санкт-Петербург."},
    }
    content.update(overrides)
    return StructuredGenerationResponse(
        model_name="strict-model",
        content=content,
        raw_response={"id": "resp-target", "choices": [{"index": 0}]},
    )


def build_orchestrator(
    tmp_path,
    provider: RecordingProvider,
):
    single_question = importlib.import_module("backend.app.generation.single_question")
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    orchestrator = single_question.SingleQuestionRegenerationOrchestrator(
        document_repository=document_repository,
        quiz_repository=quiz_repository,
        request_builder=request_builder.SingleQuestionRegenerationRequestBuilder(prompt_registry=PromptRegistry),
        provider=provider,
    )
    return orchestrator, document_repository, quiz_repository


def test_generation_mode_registry_supports_single_question_regeneration() -> None:
    assert GenerationModeRegistry.ensure_supported("single_question_regen") is GenerationMode.SINGLE_QUESTION_REGEN


def test_single_question_request_builder_assembles_targeted_provider_request() -> None:
    assert hasattr(request_builder, "SingleQuestionRegenerationRequestBuilder")
    builder = request_builder.SingleQuestionRegenerationRequestBuilder(prompt_registry=PromptRegistry)

    provider_request = builder.build(
        document=build_document(),
        quiz=build_quiz(),
        target_question=build_quiz().questions[1],
        generation_request=build_generation_request(),
        instructions="Сделай вопрос более точным.",
    )

    assert provider_request.schema_name == "question_payload"
    assert provider_request.model_name == "strict-model"
    assert provider_request.inference_parameters == {"temperature": 0.0}
    assert "single quiz question" in provider_request.system_prompt
    assert "Петр I основал Санкт-Петербург" in provider_request.user_prompt
    assert "\"quiz_id\": \"quiz-ru\"" in provider_request.user_prompt
    assert "\"question_id\": \"q-2\"" in provider_request.user_prompt
    assert "Сделай вопрос более точным." in provider_request.user_prompt
    assert "Language: ru" in provider_request.user_prompt


def test_single_question_regeneration_replaces_only_target_question_and_persists(tmp_path) -> None:
    provider = RecordingProvider([build_question_response()])
    orchestrator, document_repository, quiz_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())
    original_quiz = quiz_repository.save(build_quiz())

    result = orchestrator.regenerate(
        quiz_id=original_quiz.quiz_id,
        question_id="q-2",
        generation_request=build_generation_request(),
        instructions="Сохрани русский язык.",
    )

    persisted_quiz = quiz_repository.get(original_quiz.quiz_id)
    assert result.prompt_version == "single-question-regen-v1"
    assert result.model_name == "strict-model"
    assert result.regenerated_question.question_id == "q-2"
    assert result.quiz.questions[0] == original_quiz.questions[0]
    assert result.quiz.questions[1].prompt == "Почему Нева важна для Санкт-Петербурга?"
    assert result.quiz.questions[1].options[0].text == "Она протекает через город"
    assert persisted_quiz == result.quiz
    assert persisted_quiz.version == original_quiz.version + 1
    assert len(provider.requests) == 1
    assert provider.requests[0].model_name == "strict-model"


def test_single_question_regeneration_does_not_persist_when_provider_fails(tmp_path) -> None:
    provider = RecordingProvider(error=LLMTimeoutError("LM Studio timed out"))
    orchestrator, document_repository, quiz_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())
    original_quiz = quiz_repository.save(build_quiz())

    with pytest.raises(LLMTimeoutError):
        orchestrator.regenerate(
            quiz_id=original_quiz.quiz_id,
            question_id="q-2",
            generation_request=build_generation_request(),
            instructions=None,
        )

    assert quiz_repository.get(original_quiz.quiz_id) == original_quiz
    assert len(provider.requests) == 1


def test_single_question_regeneration_does_not_persist_invalid_replacement(tmp_path) -> None:
    provider = RecordingProvider(
        [
            build_question_response(
                options=[
                    {"option_id": "opt-1", "text": "Нева"},
                    {"option_id": "opt-2", "text": "Нева"},
                ]
            )
        ]
    )
    orchestrator, document_repository, quiz_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())
    original_quiz = quiz_repository.save(build_quiz())

    with pytest.raises(DomainValidationError, match="duplicates"):
        orchestrator.regenerate(
            quiz_id=original_quiz.quiz_id,
            question_id="q-2",
            generation_request=build_generation_request(),
            instructions=None,
        )

    assert quiz_repository.get(original_quiz.quiz_id) == original_quiz


def test_single_question_regeneration_falls_back_to_original_correct_option_index_when_model_omits_it(tmp_path) -> None:
    base_response = build_question_response()
    content_without_index = {k: v for k, v in base_response.content.items() if k != "correct_option_index"}
    provider = RecordingProvider([
        StructuredGenerationResponse(
            model_name=base_response.model_name,
            content=content_without_index,
            raw_response=base_response.raw_response,
        )
    ])
    orchestrator, document_repository, quiz_repository = build_orchestrator(tmp_path, provider)
    document_repository.save(build_document())
    original_quiz = quiz_repository.save(build_quiz())
    original_index = original_quiz.questions[1].correct_option_index

    result = orchestrator.regenerate(
        quiz_id=original_quiz.quiz_id,
        question_id="q-2",
        generation_request=build_generation_request(),
        instructions=None,
    )

    assert result.regenerated_question.correct_option_index == original_index
    assert quiz_repository.get(original_quiz.quiz_id).questions[1].correct_option_index == original_index
