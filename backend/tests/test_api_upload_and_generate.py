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


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
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


def test_direct_generation_endpoint_maps_provider_timeout_to_gateway_timeout(tmp_path) -> None:
    provider = StubProvider(error=LLMTimeoutError("LM Studio timed out"))
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_generation_payload())

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "llm_timeout_error"
