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
    """Provider test double for JSON export API flows."""

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by export tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by export tests")


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
    )


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-ru-1",
        document_id="doc-ru-1",
        title="Тренировочный квиз по географии",
        version=0,
        last_edited_at="",
        questions=(
            Question(
                question_id="question-1",
                prompt="Какой город является столицей России?",
                options=(
                    Option(option_id="option-1", text="Москва"),
                    Option(option_id="option-2", text="Казань"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Москва является столицей России."),
            ),
        ),
    )


def test_json_export_endpoint_downloads_canonical_utf8_quiz_file(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    persisted_quiz = repository.save(build_quiz())
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.get(f"/quizzes/{persisted_quiz.quiz_id}/export/json")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["content-type"].startswith("application/json; charset=utf-8")
    assert response.headers["content-disposition"] == 'attachment; filename="quiz-ru-1.json"'
    assert response.json() == persisted_quiz.to_dict()
    assert "Тренировочный квиз по географии" in response.content.decode("utf-8")
    assert "Какой город является столицей России?" in response.content.decode("utf-8")


def test_json_export_endpoint_maps_missing_quiz_to_not_found(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.get("/quizzes/quiz-missing/export/json")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
