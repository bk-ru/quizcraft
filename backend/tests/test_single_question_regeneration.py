from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.domain.models import Explanation
from backend.app.domain.models import Option
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.main import create_app
from backend.app.storage.quizzes import FileSystemQuizRepository


class StubProvider:
    """Provider test double for single-question regeneration contract tests."""

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by contract tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by contract tests")


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
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


def build_client(tmp_path) -> tuple[TestClient, FileSystemQuizRepository]:
    repository = FileSystemQuizRepository(tmp_path)
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    return TestClient(app), repository


def test_single_question_regeneration_contract_validates_existing_question_without_mutation(tmp_path) -> None:
    client, repository = build_client(tmp_path)
    persisted_quiz = repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-2/regenerate",
        json={
            "quiz_id": persisted_quiz.quiz_id,
            "question_id": "q-2",
            "instructions": "Сделай вопрос точнее, сохрани русский язык.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["quiz_id"] == persisted_quiz.quiz_id
    assert body["question_id"] == "q-2"
    assert body["target_question"]["prompt"] == "Какая река протекает через Санкт-Петербург?"
    assert body["target_question"]["options"][0]["text"] == "Нева"
    assert body["target_question"]["explanation"] == {"text": "Через Санкт-Петербург протекает Нева."}
    assert body["request"]["instructions"] == "Сделай вопрос точнее, сохрани русский язык."
    assert body["regeneration"] == {
        "status": "contract_validated",
        "provider_call": False,
        "quiz_mutated": False,
        "prompt_mode": "not_configured",
    }
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert repository.get(persisted_quiz.quiz_id) == persisted_quiz


def test_single_question_regeneration_contract_allows_minimal_empty_request_body(tmp_path) -> None:
    client, repository = build_client(tmp_path)
    persisted_quiz = repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-1/regenerate",
        json={},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["question_id"] == "q-1"
    assert body["request"] == {}
    assert body["regeneration"]["provider_call"] is False
    assert repository.get(persisted_quiz.quiz_id) == persisted_quiz


def test_single_question_regeneration_contract_maps_missing_quiz_to_not_found(tmp_path) -> None:
    client, _repository = build_client(tmp_path)

    response = client.post(
        "/quizzes/quiz-missing/questions/q-1/regenerate",
        json={},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_single_question_regeneration_contract_maps_missing_question_to_not_found(tmp_path) -> None:
    client, repository = build_client(tmp_path)
    persisted_quiz = repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-missing/regenerate",
        json={},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert repository.get(persisted_quiz.quiz_id) == persisted_quiz


def test_single_question_regeneration_contract_rejects_mismatched_quiz_boundary(tmp_path) -> None:
    client, repository = build_client(tmp_path)
    persisted_quiz = repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-1/regenerate",
        json={"quiz_id": "other-quiz"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "quiz_id in payload must match path" in response.json()["error"]["message"]
    assert repository.get(persisted_quiz.quiz_id) == persisted_quiz


def test_single_question_regeneration_contract_rejects_mismatched_question_boundary(tmp_path) -> None:
    client, repository = build_client(tmp_path)
    persisted_quiz = repository.save(build_quiz())

    response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-1/regenerate",
        json={"question_id": "q-2"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "question_id in payload must match path" in response.json()["error"]["message"]
    assert repository.get(persisted_quiz.quiz_id) == persisted_quiz


def test_single_question_regeneration_contract_rejects_invalid_request_payload(tmp_path) -> None:
    client, repository = build_client(tmp_path)
    persisted_quiz = repository.save(build_quiz())

    blank_response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-1/regenerate",
        json={"instructions": "   "},
    )
    extra_field_response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-1/regenerate",
        json={"unexpected": "value"},
    )
    non_string_response = client.post(
        f"/quizzes/{persisted_quiz.quiz_id}/questions/q-1/regenerate",
        json={"question_id": 1},
    )

    assert blank_response.status_code == 422
    assert blank_response.json()["error"]["code"] == "validation_error"
    assert "instructions" in blank_response.json()["error"]["message"]
    assert extra_field_response.status_code == 422
    assert extra_field_response.json()["error"]["code"] == "validation_error"
    assert "unexpected" in extra_field_response.json()["error"]["message"]
    assert non_string_response.status_code == 422
    assert non_string_response.json()["error"]["code"] == "validation_error"
    assert "question_id" in non_string_response.json()["error"]["message"]
    assert repository.get(persisted_quiz.quiz_id) == persisted_quiz
