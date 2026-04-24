from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.core.config import GenerationProfile
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.main import create_app


class RecordingProvider:
    """Provider test double recording generation requests."""

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
                "quiz_id": f"quiz-{len(self.requests)}",
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
            raw_response={"id": f"resp-{len(self.requests)}", "choices": [{"index": 0}]},
        )

    def embed(self, request):
        raise AssertionError("embed should not be called in settings API tests")


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


def build_settings_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "question_count": 2,
        "language": "ru",
        "difficulty": "medium",
        "quiz_type": "single_choice",
        "generation_mode": "direct",
        "profile_name": "balanced",
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


def test_generation_settings_api_saves_and_loads_settings(tmp_path) -> None:
    app = create_app(config=build_config(), provider=RecordingProvider(), storage_root=tmp_path)
    client = TestClient(app)

    save_response = client.put("/generation/settings", json=build_settings_payload(profile_name="strict"))
    load_response = client.get("/generation/settings")

    assert save_response.status_code == 200
    assert load_response.status_code == 200
    assert save_response.json()["settings"] == load_response.json()["settings"]
    assert load_response.json()["settings"]["profile_name"] == "strict"
    assert load_response.json()["settings"]["language"] == "ru"


def test_generation_settings_api_rejects_invalid_model_and_profile(tmp_path) -> None:
    app = create_app(config=build_config(), provider=RecordingProvider(), storage_root=tmp_path)
    client = TestClient(app)

    model_response = client.put(
        "/generation/settings",
        json=build_settings_payload(model_name="rogue-model"),
    )
    profile_response = client.put(
        "/generation/settings",
        json=build_settings_payload(profile_name="experimental"),
    )

    assert model_response.status_code == 422
    assert model_response.json()["error"]["code"] == "model_selection_error"
    assert profile_response.status_code == 422
    assert profile_response.json()["error"]["code"] == "generation_profile_error"


def test_generate_endpoint_reuses_saved_settings_for_partial_request(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    settings_response = client.put(
        "/generation/settings",
        json=build_settings_payload(profile_name="strict"),
    )
    response = client.post(
        f"/documents/{document_id}/generate",
        json={"question_count": 2},
    )

    assert settings_response.status_code == 200
    assert response.status_code == 200
    assert response.json()["model_name"] == "strict-model"
    assert response.json()["quiz"]["title"] == "Квиз по русскому документу"
    assert provider.requests[0].model_name == "strict-model"
    assert provider.requests[0].inference_parameters["temperature"] == 0.0


def test_generate_endpoint_persists_successful_request_as_future_defaults(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    first_response = client.post(
        f"/documents/{document_id}/generate",
        json=build_settings_payload(profile_name="strict"),
    )
    second_response = client.post(
        f"/documents/{document_id}/generate",
        json={"question_count": 2},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert provider.requests[0].model_name == "strict-model"
    assert provider.requests[1].model_name == "strict-model"


def test_generate_endpoint_rejects_partial_request_without_saved_settings(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json={"question_count": 2},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "generation_settings_error"
    assert provider.requests == []


def test_generate_endpoint_keeps_existing_full_request_behavior(tmp_path) -> None:
    provider = RecordingProvider()
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(f"/documents/{document_id}/generate", json=build_settings_payload())

    assert response.status_code == 200
    assert response.json()["model_name"] == "local-model"
    assert provider.requests[0].model_name is None
    assert provider.requests[0].inference_parameters["temperature"] == 0.2
