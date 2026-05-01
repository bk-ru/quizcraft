from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.core.config import ConfigurationError
from backend.app.domain.errors import ProviderDisabledError
from backend.app.llm.external_api import ExternalAPIClient
from backend.app.llm.factory import build_provider_runtime
from backend.app.llm.registry import ProviderName
from backend.app.main import create_app


class FakeHTTPResponse:
    """Minimal context-manager response used to stub urllib calls."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def read(self) -> bytes:
        """Return the prepared raw response payload."""

        return self._payload

    def __enter__(self) -> "FakeHTTPResponse":
        """Return the response for context-manager usage."""

        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Propagate exceptions raised inside the context manager."""

        return False


@pytest.fixture(autouse=True)
def _isolate_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Point the config loader at an empty path so real ``.env`` files never leak into tests."""

    monkeypatch.setenv("QUIZCRAFT_ENV_FILE", str(tmp_path / "missing.env"))


def build_external_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        external_api_base_url="https://api.example.test/v1",
        external_api_key="test-token",
        external_api_model="external-quiz-model",
        external_api_embedding_model="external-embed-model",
        providers_enabled=(ProviderName.EXTERNAL_API,),
        default_provider=ProviderName.EXTERNAL_API,
        log_format="%(levelname)s:%(message)s",
    )


def build_lm_studio_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        external_api_base_url="https://api.example.test/v1",
        external_api_model="external-quiz-model",
        external_api_embedding_model="external-embed-model",
        allowed_models=("local-model", "external-quiz-model"),
        log_format="%(levelname)s:%(message)s",
    )


def test_from_env_loads_external_api_provider_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LM_STUDIO_MODEL", "local-model")
    monkeypatch.setenv("PROVIDERS_ENABLED", "external_api")
    monkeypatch.setenv("DEFAULT_PROVIDER", "external_api")
    monkeypatch.setenv("EXTERNAL_API_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("EXTERNAL_API_API_KEY", "secret-token")
    monkeypatch.setenv("EXTERNAL_API_MODEL", "external-quiz-model")
    monkeypatch.setenv("EXTERNAL_API_EMBEDDING_MODEL", "external-embed-model")

    config = AppConfig.from_env()

    assert config.providers_enabled == (ProviderName.EXTERNAL_API,)
    assert config.default_provider is ProviderName.EXTERNAL_API
    assert config.default_model == "external-quiz-model"
    assert config.external_api_base_url == "https://api.example.test/v1"
    assert config.external_api_key == "secret-token"
    assert config.external_api_model == "external-quiz-model"
    assert config.external_api_embedding_model == "external-embed-model"
    assert config.allowed_models == ("local-model", "external-quiz-model")


def test_external_api_provider_requires_base_url_and_model_when_enabled() -> None:
    with pytest.raises(ConfigurationError, match="EXTERNAL_API_BASE_URL"):
        AppConfig(
            lm_studio_base_url="http://localhost:1234/v1",
            lm_studio_model="local-model",
            providers_enabled=(ProviderName.EXTERNAL_API,),
            default_provider=ProviderName.EXTERNAL_API,
        )

    with pytest.raises(ConfigurationError, match="EXTERNAL_API_MODEL"):
        AppConfig(
            lm_studio_base_url="http://localhost:1234/v1",
            lm_studio_model="local-model",
            external_api_base_url="https://api.example.test/v1",
            providers_enabled=(ProviderName.EXTERNAL_API,),
            default_provider=ProviderName.EXTERNAL_API,
        )


def test_external_api_model_must_be_allowed_when_allowed_models_are_explicit() -> None:
    with pytest.raises(ConfigurationError, match="EXTERNAL_API_MODEL"):
        AppConfig(
            lm_studio_base_url="http://localhost:1234/v1",
            lm_studio_model="local-model",
            external_api_base_url="https://api.example.test/v1",
            external_api_model="external-quiz-model",
            allowed_models=("local-model",),
            providers_enabled=(ProviderName.EXTERNAL_API,),
            default_provider=ProviderName.EXTERNAL_API,
        )


def test_build_provider_runtime_registers_external_api_as_active_provider() -> None:
    runtime = build_provider_runtime(build_external_config())

    assert runtime.registry.registered_provider_names == (ProviderName.EXTERNAL_API,)
    assert isinstance(runtime.active_provider.provider, ExternalAPIClient)


def test_build_provider_runtime_does_not_initialize_external_api_when_disabled() -> None:
    runtime = build_provider_runtime(build_lm_studio_config())

    assert ProviderName.EXTERNAL_API not in runtime.registry.registered_provider_names


def test_build_provider_runtime_wraps_disabled_external_api_provider() -> None:
    config = AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        external_api_base_url="https://api.example.test/v1",
        external_api_model="external-quiz-model",
        allowed_models=("local-model", "external-quiz-model"),
        providers_enabled=(ProviderName.LM_STUDIO,),
        default_provider=ProviderName.EXTERNAL_API,
        log_format="%(levelname)s:%(message)s",
    )
    runtime = build_provider_runtime(config)

    with pytest.raises(ProviderDisabledError, match="external_api"):
        runtime.active_provider.embed(request=None)


def test_external_api_health_endpoint_returns_provider_status(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        return FakeHTTPResponse({"data": [{"id": "external-quiz-model"}]})

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)
    app = create_app(config=build_external_config(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.get("/health/external-api")

    assert response.status_code == 200
    assert response.json() == {
        "status": "available",
        "message": "External API is available",
        "default_model": "external-quiz-model",
        "embedding_model": "external-embed-model",
    }
    assert captured == {
        "url": "https://api.example.test/v1/models",
        "authorization": "Bearer test-token",
    }


def test_external_api_health_endpoint_reports_disabled_provider_without_calling_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    def fake_urlopen(request, timeout):
        raise AssertionError("urlopen should not be called for disabled external API health")

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)
    app = create_app(config=build_lm_studio_config(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.get("/health/external-api")

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "message": "Provider 'external_api' is disabled by PROVIDERS_ENABLED",
        "default_model": "external-quiz-model",
        "embedding_model": "external-embed-model",
    }
