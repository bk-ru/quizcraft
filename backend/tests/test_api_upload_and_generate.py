from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.main import create_app
from backend.app.storage.documents import FileSystemDocumentRepository


class StubProvider:
    """Provider test double for upload and generate API flows."""

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
        raise AssertionError("embed should not be called in upload or generate API tests")


def build_config(max_document_chars: int = 50_000) -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        max_document_chars=max_document_chars,
        log_format="%(levelname)s:%(message)s",
    )


def build_generation_payload() -> dict[str, object]:
    return {
        "question_count": 2,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": "direct",
    }


def build_provider_response() -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        model_name="local-model",
        content={
            "quiz_id": "quiz-generated",
            "document_id": "ignored-by-normalizer",
            "title": "Generated quiz",
            "version": 1,
            "last_edited_at": "2026-04-18T12:00:00Z",
            "questions": [
                {
                    "question_id": "q-1",
                    "prompt": "Question 1?",
                    "options": [
                        {"option_id": "opt-1", "text": "Option A"},
                        {"option_id": "opt-2", "text": "Option B"},
                    ],
                    "correct_option_index": 0,
                    "explanation": {"text": "Explanation 1."},
                },
                {
                    "question_id": "q-2",
                    "prompt": "Question 2?",
                    "options": [
                        {"option_id": "opt-1", "text": "Option A"},
                        {"option_id": "opt-2", "text": "Option B"},
                    ],
                    "correct_option_index": 0,
                    "explanation": {"text": "Explanation 2."},
                },
            ],
        },
        raw_response={"id": "resp-1", "choices": [{"index": 0}]},
    )


def upload_document(client: TestClient) -> str:
    response = client.post(
        "/documents",
        content=b"First fact.\nSecond fact.",
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def upload_russian_document(client: TestClient) -> str:
    response = client.post(
        "/documents",
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def test_document_upload_endpoint_persists_valid_file_and_returns_metadata(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content=b"First fact.\nSecond fact.",
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    payload = response.json()
    persisted = FileSystemDocumentRepository(tmp_path).get(payload["document_id"])
    assert payload["filename"] == "lecture.txt"
    assert payload["media_type"] == "text/plain"
    assert payload["file_size_bytes"] == len(b"First fact.\nSecond fact.")
    assert payload["metadata"]["text_length"] == len("First fact.\nSecond fact.")
    assert response.headers["X-Request-ID"] == payload["request_id"]
    assert persisted.document_id == payload["document_id"]


def test_document_upload_endpoint_rejects_invalid_file(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content=b"image",
        headers={"X-Filename": "lecture.png", "Content-Type": "image/png"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "file_validation_error"


def test_direct_generation_endpoint_returns_generated_quiz_for_existing_document(tmp_path) -> None:
    provider = StubProvider(responses=[build_provider_response()])
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["quiz_id"] == payload["quiz"]["quiz_id"]
    assert payload["quiz"]["document_id"] == document_id
    assert payload["model_name"] == "local-model"
    assert payload["prompt_version"] == "direct-v1"
    assert len(payload["quiz"]["questions"]) == 2
    assert "Question count: 2" in provider.requests[0].user_prompt


def test_direct_generation_endpoint_maps_missing_document_to_not_found(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post("/documents/doc-missing/generate", json=build_generation_payload())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_direct_generation_endpoint_rejects_unknown_difficulty(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["difficulty"] = "insane"

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "difficulty" in body["error"]["message"]
    assert "easy" in body["error"]["message"]


def test_direct_generation_endpoint_rejects_unknown_quiz_type(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["quiz_type"] = "multi_choice"

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "quiz_type" in body["error"]["message"]


def test_direct_generation_endpoint_rejects_unknown_language(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)
    payload = build_generation_payload()
    payload["language"] = "русский"

    response = client.post(f"/documents/{document_id}/generate", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "language" in body["error"]["message"]


def test_direct_generation_endpoint_maps_oversized_document_to_413(tmp_path) -> None:
    provider = StubProvider()
    app = create_app(config=build_config(max_document_chars=10), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "document_too_large_for_generation"
    assert document_id in body["error"]["message"]
    assert provider.requests == []


def test_direct_generation_endpoint_maps_provider_timeout_to_gateway_timeout(tmp_path) -> None:
    provider = StubProvider(error=LLMTimeoutError("LM Studio timed out"))
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "llm_timeout_error"


def test_document_upload_endpoint_preserves_russian_text_in_storage(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    persisted = FileSystemDocumentRepository(tmp_path).get(response.json()["document_id"])
    assert persisted.normalized_text == "Первый факт.\nВторой факт."


def test_document_upload_endpoint_accepts_russian_filename_query_param(tmp_path) -> None:
    app = create_app(config=build_config(), provider=StubProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/documents",
        params={"filename": "тестовый-конспект.txt"},
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 201
    payload = response.json()
    persisted = FileSystemDocumentRepository(tmp_path).get(payload["document_id"])
    assert payload["filename"] == "тестовый-конспект.txt"
    assert persisted.filename == "тестовый-конспект.txt"
    assert persisted.normalized_text == "Первый факт.\nВторой факт."


def test_direct_generation_endpoint_returns_russian_quiz_for_russian_document(tmp_path) -> None:
    provider = StubProvider(
        responses=[
            StructuredGenerationResponse(
                model_name="local-model",
                content={
                    "quiz_id": "quiz-ru",
                    "document_id": "ignored-by-normalizer",
                    "title": "Русский квиз",
                    "version": 1,
                    "last_edited_at": "2026-04-18T12:00:00Z",
                    "questions": [
                        {
                            "question_id": "q-1",
                            "prompt": "Что указано в документе?",
                            "options": [
                                {"option_id": "opt-1", "text": "Первый факт"},
                                {"option_id": "opt-2", "text": "Третий факт"},
                            ],
                            "correct_option_index": 0,
                            "explanation": {"text": "В документе есть первый факт."},
                        },
                        {
                            "question_id": "q-2",
                            "prompt": "Сколько фактов перечислено?",
                            "options": [
                                {"option_id": "opt-1", "text": "Два"},
                                {"option_id": "opt-2", "text": "Четыре"},
                            ],
                            "correct_option_index": 0,
                            "explanation": {"text": "В документе перечислены два факта."},
                        },
                    ],
                },
                raw_response={"id": "resp-ru-1", "choices": [{"index": 0}]},
            )
        ]
    )
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["quiz"]["title"] == "Русский квиз"
    assert payload["quiz"]["document_id"] == document_id
    assert payload["quiz"]["questions"][0]["prompt"] == "Что указано в документе?"
    assert payload["quiz"]["questions"][0]["options"][0]["text"] == "Первый факт"
    assert payload["quiz"]["questions"][0]["explanation"] == {"text": "В документе есть первый факт."}
