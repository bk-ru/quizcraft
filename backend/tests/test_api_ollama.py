from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.llm.registry import ProviderName
from backend.app.main import create_app


class FakeHTTPResponse:
    """Minimal context-manager response used to stub urllib calls."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        """Return the prepared raw response payload."""

        return self._payload

    def __enter__(self) -> "FakeHTTPResponse":
        """Return the response for context-manager usage."""

        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Propagate exceptions raised inside the context manager."""

        return False


def build_ollama_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:7b",
        ollama_embedding_model="nomic-embed-text",
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.OLLAMA,
        log_format="%(levelname)s:%(message)s",
    )


def build_lm_studio_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        ollama_model="qwen2.5:7b",
        ollama_embedding_model="nomic-embed-text",
        allowed_models=("local-model", "qwen2.5:7b"),
        log_format="%(levelname)s:%(message)s",
    )


def upload_russian_document(client: TestClient) -> str:
    response = client.post(
        "/documents",
        content="Москва — столица России. В документе два факта.".encode("utf-8"),
        headers={"X-Filename": "lecture.txt", "Content-Type": "text/plain"},
    )
    assert response.status_code == 201
    return response.json()["document_id"]


def test_ollama_health_endpoint_returns_provider_status(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeHTTPResponse({"models": [{"name": "qwen2.5:7b"}]})

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)
    app = create_app(config=build_ollama_config(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.get("/health/ollama")

    assert response.status_code == 200
    assert response.json() == {
        "status": "available",
        "message": "Ollama is available",
        "default_model": "qwen2.5:7b",
        "embedding_model": "nomic-embed-text",
    }
    assert captured == {"url": "http://localhost:11434/api/tags", "timeout": 300}


def test_ollama_health_endpoint_reports_disabled_provider_without_calling_provider(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        raise AssertionError("urlopen should not be called for disabled Ollama health")

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)
    app = create_app(config=build_lm_studio_config(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.get("/health/ollama")

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "message": "Provider 'ollama' is disabled by PROVIDERS_ENABLED",
        "default_model": "qwen2.5:7b",
        "embedding_model": "nomic-embed-text",
    }


def test_direct_generation_endpoint_uses_ollama_active_provider_and_preserves_cyrillic(
    monkeypatch,
    tmp_path,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "qwen2.5:7b",
                "message": {
                    "content": json.dumps(
                        {
                            "quiz_id": "quiz-ollama",
                            "document_id": "ignored-by-normalizer",
                            "title": "Квиз по русскому документу",
                            "version": 1,
                            "last_edited_at": "2026-04-26T12:00:00Z",
                            "questions": [
                                {
                                    "question_id": "q-1",
                                    "prompt": "Что является столицей России?",
                                    "options": [
                                        {"option_id": "opt-1", "text": "Москва"},
                                        {"option_id": "opt-2", "text": "Казань"},
                                    ],
                                    "correct_option_index": 0,
                                    "explanation": {"text": "В документе указана Москва."},
                                },
                                {
                                    "question_id": "q-2",
                                    "prompt": "Сколько фактов указано в документе?",
                                    "options": [
                                        {"option_id": "opt-1", "text": "Два"},
                                        {"option_id": "opt-2", "text": "Пять"},
                                    ],
                                    "correct_option_index": 0,
                                    "explanation": {"text": "В документе два факта."},
                                },
                            ],
                        },
                        ensure_ascii=False,
                    )
                },
            }
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)
    app = create_app(config=build_ollama_config(), storage_root=tmp_path)
    client = TestClient(app)
    document_id = upload_russian_document(client)

    response = client.post(
        f"/documents/{document_id}/generate",
        json={
            "question_count": 2,
            "language": "ru",
            "difficulty": "medium",
            "quiz_type": "single_choice",
            "generation_mode": "direct",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["quiz"]["title"] == "Квиз по русскому документу"
    assert body["quiz"]["questions"][0]["prompt"] == "Что является столицей России?"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["model"] == "qwen2.5:7b"
    assert "Москва — столица России" in captured["payload"]["messages"][1]["content"]
