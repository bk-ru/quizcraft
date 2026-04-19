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
    """Provider test double for quiz update API flows."""

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by quiz update tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by quiz update tests")


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
    )


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-1",
        document_id="doc-1",
        title="Generated quiz",
        version=0,
        last_edited_at="",
        questions=(
            Question(
                question_id="q-1",
                prompt="Question 1?",
                options=(
                    Option(option_id="opt-1", text="Option A"),
                    Option(option_id="opt-2", text="Option B"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Explanation 1."),
            ),
        ),
    )


def test_quiz_update_endpoint_persists_valid_changes_and_returns_saved_quiz(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    original_quiz = repository.save(build_quiz())
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    updated_payload = original_quiz.to_dict()
    updated_payload["title"] = "Edited quiz title"
    updated_payload["questions"][0]["prompt"] = "Edited question?"
    updated_payload["questions"][0]["explanation"] = {"text": "Updated explanation."}

    response = client.put(f"/quizzes/{original_quiz.quiz_id}", json={"quiz": updated_payload})

    assert response.status_code == 200
    body = response.json()
    persisted_quiz = repository.get(original_quiz.quiz_id)
    assert body["quiz_id"] == original_quiz.quiz_id
    assert body["quiz"]["title"] == "Edited quiz title"
    assert body["quiz"]["questions"][0]["prompt"] == "Edited question?"
    assert body["quiz"]["questions"][0]["explanation"] == {"text": "Updated explanation."}
    assert body["quiz"]["version"] == original_quiz.version + 1
    assert body["quiz"]["last_edited_at"] != original_quiz.last_edited_at
    assert body["quiz"] == persisted_quiz.to_dict()
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_quiz_update_endpoint_rejects_invalid_quiz_payload(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    original_quiz = repository.save(build_quiz())
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    invalid_payload = original_quiz.to_dict()
    invalid_payload["questions"][0]["options"][1]["text"] = "Option A"

    response = client.put(f"/quizzes/{original_quiz.quiz_id}", json={"quiz": invalid_payload})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert repository.get(original_quiz.quiz_id) == original_quiz


def test_quiz_update_endpoint_maps_missing_quiz_to_not_found(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.put("/quizzes/quiz-missing", json={"quiz": build_quiz().to_dict()})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
