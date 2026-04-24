from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.core.config import GenerationProfile
from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import Explanation
from backend.app.domain.models import GenerationSettings
from backend.app.domain.models import Option
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.main import create_app
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_settings import FileSystemGenerationSettingsRepository
from backend.app.storage.quizzes import FileSystemQuizRepository


class RecordingProvider:
    """Provider test double for single-question regeneration API flows."""

    def __init__(
        self,
        responses: list[StructuredGenerationResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._error = error
        self.requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        if not self._responses:
            raise AssertionError("provider was called more times than expected")
        return self._responses.pop(0)

    def embed(self, request):
        raise AssertionError("embed should not be called by single-question regeneration tests")


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        allowed_models=("local-model", "strict-model"),
        generation_profiles={
            "balanced": GenerationProfile(
                name="balanced",
                inference_parameters={"temperature": 0.2},
            ),
            "strict": GenerationProfile(
                name="strict",
                model_name="strict-model",
                inference_parameters={"temperature": 0.0},
            ),
        },
        default_generation_profile="balanced",
        log_format="%(levelname)s:%(message)s",
    )


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


def build_client(
    tmp_path,
    provider: RecordingProvider,
) -> tuple[TestClient, FileSystemQuizRepository, FileSystemGenerationSettingsRepository]:
    document_repository = FileSystemDocumentRepository(tmp_path)
    quiz_repository = FileSystemQuizRepository(tmp_path)
    settings_repository = FileSystemGenerationSettingsRepository(tmp_path)
    document_repository.save(build_document())
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    return TestClient(app), quiz_repository, settings_repository


def test_single_question_regeneration_endpoint_replaces_only_target_question_and_persists(tmp_path) -> None:
    provider = RecordingProvider([build_question_response()])
    client, quiz_repository, _settings_repository = build_client(tmp_path, provider)
    original_quiz = quiz_repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-2/regenerate",
        json={
            "quiz_id": original_quiz.quiz_id,
            "question_id": "q-2",
            "instructions": "Сделай вопрос точнее, сохрани русский язык.",
            "profile_name": "strict",
        },
    )

    assert response.status_code == 200
    body = response.json()
    persisted_quiz = quiz_repository.get(original_quiz.quiz_id)
    assert body["quiz_id"] == original_quiz.quiz_id
    assert body["question_id"] == "q-2"
    assert body["model_name"] == "strict-model"
    assert body["prompt_version"] == "single-question-regen-v1"
    assert body["quiz"]["questions"][0] == original_quiz.to_dict()["questions"][0]
    assert body["quiz"]["questions"][1]["question_id"] == "q-2"
    assert body["quiz"]["questions"][1]["prompt"] == "Почему Нева важна для Санкт-Петербурга?"
    assert body["quiz"]["questions"][1]["options"][0]["text"] == "Она протекает через город"
    assert body["regenerated_question"] == body["quiz"]["questions"][1]
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["quiz"] == persisted_quiz.to_dict()
    assert persisted_quiz.version == original_quiz.version + 1
    assert len(provider.requests) == 1
    assert provider.requests[0].model_name == "strict-model"
    assert provider.requests[0].inference_parameters["temperature"] == 0.0
    assert "Сделай вопрос точнее" in provider.requests[0].user_prompt


def test_single_question_regeneration_endpoint_reuses_saved_profile_settings(tmp_path) -> None:
    provider = RecordingProvider([build_question_response()])
    client, quiz_repository, settings_repository = build_client(tmp_path, provider)
    original_quiz = quiz_repository.save(build_quiz())
    settings_repository.save(
        GenerationSettings(
            question_count=3,
            language="ru",
            difficulty="hard",
            quiz_type="single_choice",
            generation_mode=GenerationMode.DIRECT,
            model_name=None,
            profile_name="strict",
        )
    )

    response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-2/regenerate",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["model_name"] == "strict-model"
    assert provider.requests[0].model_name == "strict-model"
    assert provider.requests[0].inference_parameters["temperature"] == 0.0
    assert "Difficulty: hard" in provider.requests[0].user_prompt
    assert quiz_repository.get(original_quiz.quiz_id).questions[0] == original_quiz.questions[0]


def test_single_question_regeneration_endpoint_maps_missing_quiz_to_not_found(tmp_path) -> None:
    provider = RecordingProvider([build_question_response()])
    client, _quiz_repository, _settings_repository = build_client(tmp_path, provider)

    response = client.post(
        "/quizzes/quiz-missing/questions/q-1/regenerate",
        json={},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert provider.requests == []


def test_single_question_regeneration_endpoint_maps_missing_question_to_not_found(tmp_path) -> None:
    provider = RecordingProvider([build_question_response()])
    client, quiz_repository, _settings_repository = build_client(tmp_path, provider)
    original_quiz = quiz_repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-missing/regenerate",
        json={},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert provider.requests == []
    assert quiz_repository.get(original_quiz.quiz_id) == original_quiz


def test_single_question_regeneration_endpoint_rejects_invalid_request_payload(tmp_path) -> None:
    provider = RecordingProvider([build_question_response()])
    client, quiz_repository, _settings_repository = build_client(tmp_path, provider)
    original_quiz = quiz_repository.save(build_quiz())

    blank_response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-1/regenerate",
        json={"instructions": "   "},
    )
    extra_field_response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-1/regenerate",
        json={"unexpected": "value"},
    )
    boundary_response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-1/regenerate",
        json={"question_id": "q-2"},
    )

    assert blank_response.status_code == 422
    assert blank_response.json()["error"]["code"] == "validation_error"
    assert "instructions" in blank_response.json()["error"]["message"]
    assert extra_field_response.status_code == 422
    assert extra_field_response.json()["error"]["code"] == "validation_error"
    assert "unexpected" in extra_field_response.json()["error"]["message"]
    assert boundary_response.status_code == 422
    assert boundary_response.json()["error"]["code"] == "validation_error"
    assert "question_id in payload must match path" in boundary_response.json()["error"]["message"]
    assert provider.requests == []
    assert quiz_repository.get(original_quiz.quiz_id) == original_quiz


def test_single_question_regeneration_endpoint_preserves_quiz_when_provider_fails(tmp_path) -> None:
    provider = RecordingProvider(error=LLMTimeoutError("LM Studio timed out"))
    client, quiz_repository, _settings_repository = build_client(tmp_path, provider)
    original_quiz = quiz_repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-2/regenerate",
        json={"profile_name": "strict"},
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "llm_timeout_error"
    assert len(provider.requests) == 1
    assert quiz_repository.get(original_quiz.quiz_id) == original_quiz


def test_single_question_regeneration_endpoint_preserves_quiz_when_replacement_is_invalid(tmp_path) -> None:
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
    client, quiz_repository, _settings_repository = build_client(tmp_path, provider)
    original_quiz = quiz_repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{original_quiz.quiz_id}/questions/q-2/regenerate",
        json={"profile_name": "strict"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert len(provider.requests) == 1
    assert quiz_repository.get(original_quiz.quiz_id) == original_quiz
