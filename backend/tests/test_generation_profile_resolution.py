from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.core.config import GenerationProfile
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.main import create_app


class RecordingProvider:
    """Provider test double recording structured generation requests."""

    def __init__(self) -> None:
        self.requests: list[StructuredGenerationRequest] = []

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self.requests.append(request)
        model_name = request.model_name or "local-model"
        return StructuredGenerationResponse(
            model_name=model_name,
            content={
                "quiz_id": "quiz-ru",
                "document_id": "ignored-by-normalizer",
                "title": "Квиз по русскому документу",
                "version": 1,
                "last_edited_at": "2026-04-24T12:00:00Z",
                "questions": [
                    {
                        "question_id": "q-1",
                        "prompt": "Что описывает документ?",
                        "options": [
                            {"option_id": "opt-1", "text": "Первый факт"},
                            {"option_id": "opt-2", "text": "Третий факт"},
                        ],
                        "correct_option_index": 0,
                        "explanation": {"text": "В документе указан первый факт."},
                    },
                    {
                        "question_id": "q-2",
                        "prompt": "Сколько фактов приведено?",
                        "options": [
                            {"option_id": "opt-1", "text": "Два"},
                            {"option_id": "opt-2", "text": "Пять"},
                        ],
                        "correct_option_index": 0,
                        "explanation": {"text": "В документе приведены два факта."},
                    },
                ],
            },
            raw_response={"id": "resp-ru", "choices": [{"index": 0}]},
        )

    def embed(self, request):
        raise AssertionError("embed should not be called in profile resolution tests")


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


def build_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "question_count": 2,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": "direct",
    }
    payload.update(overrides)
    return payload


def upload_russian_document(client: TestClient) -> str:
    response = client.post(
        "/documents",
        content="Первый факт.\nВторой факт.".encode("utf-8"),
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def test_generate_endpoint_resolves_named_profile_model_and_inference_parameters(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_payload(profile_name="strict"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] == "strict-model"
    assert body["quiz"]["title"] == "Квиз по русскому документу"
    assert provider.requests[0].model_name == "strict-model"
    assert provider.requests[0].inference_parameters["temperature"] == 0.0


def test_generate_endpoint_accepts_explicit_allowed_model_over_profile_model(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_payload(profile_name="strict", model_name="local-model"),
    )

    assert response.status_code == 200
    assert response.json()["model_name"] == "local-model"
    assert provider.requests[0].model_name == "local-model"
    assert provider.requests[0].inference_parameters["temperature"] == 0.0


def test_generate_endpoint_rejects_model_outside_whitelist(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_payload(model_name="rogue-model"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "model_selection_error"
    assert provider.requests == []


def test_generate_endpoint_rejects_unknown_profile(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json=build_payload(profile_name="experimental"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "generation_profile_error"
    assert provider.requests == []


def test_generate_endpoint_keeps_existing_request_shape_compatible(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] == "local-model"
    assert body["quiz"]["questions"][0]["prompt"] == "Что описывает документ?"
    assert provider.requests[0].model_name is None
    assert provider.requests[0].inference_parameters["temperature"] == 0.2
