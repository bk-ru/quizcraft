import logging

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.domain.models import ProviderHealthStatus
from backend.app.llm.factory import ProviderRuntime
from backend.app.llm.registry import ProviderName
from backend.app.llm.registry import ProviderRegistry
from backend.app.main import create_app


class StubProvider:
    """Test double для проверок состояния API."""

    def healthcheck(self):
        raise AssertionError("LM Studio healthcheck should not be called by /health")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by health tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by health tests")


class HealthProvider:
    def __init__(self, status: str = "available", message: str = "Provider is available") -> None:
        self._status = status
        self._message = message
        self.healthcheck_calls = 0

    def healthcheck(self) -> ProviderHealthStatus:
        self.healthcheck_calls += 1
        return ProviderHealthStatus(status=self._status, message=self._message)

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by health tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by health tests")


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
    )


def build_ollama_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        ollama_model="qwen2.5:7b",
        ollama_embedding_model="nomic-embed-text",
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.OLLAMA,
        log_format="%(levelname)s:%(message)s",
    )


def build_disabled_default_provider_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        ollama_model="qwen2.5:7b",
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.LM_STUDIO,
        log_format="%(levelname)s:%(message)s",
    )


def test_backend_health_endpoint_returns_backend_status_and_basic_config_info() -> None:
    app = create_app(config=build_config(), provider=StubProvider())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "default_provider": "lm_studio",
        "default_model": "local-model",
        "generation_modes": ["direct", "single_question_regen", "rag"],
        "providers_enabled": ["lm_studio"],
    }
    assert response.headers["X-Request-ID"]


def test_active_provider_health_endpoint_checks_configured_default_provider(tmp_path) -> None:
    provider = HealthProvider(message="Ollama is available")
    app = create_app(config=build_ollama_config(), storage_root=tmp_path)
    app.state.provider_registry = ProviderRegistry(
        providers={ProviderName.OLLAMA: provider},
        enabled_providers=(ProviderName.OLLAMA,),
    )
    client = TestClient(app)

    response = client.get("/health/provider")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "ollama",
        "status": "available",
        "message": "Ollama is available",
        "default_model": "qwen2.5:7b",
        "embedding_model": "nomic-embed-text",
        "available_models": [],
    }
    assert provider.healthcheck_calls == 1


def test_active_provider_health_endpoint_reports_disabled_default_without_calling_provider(tmp_path) -> None:
    provider = HealthProvider()
    app = create_app(config=build_disabled_default_provider_config(), storage_root=tmp_path)
    app.state.provider_registry = ProviderRegistry(
        providers={ProviderName.LM_STUDIO: provider},
        enabled_providers=(ProviderName.OLLAMA,),
    )
    client = TestClient(app)

    response = client.get("/health/provider")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "lm_studio",
        "status": "disabled",
        "message": "Provider 'lm_studio' is disabled by PROVIDERS_ENABLED",
        "default_model": "local-model",
        "embedding_model": "local-model",
        "available_models": [],
    }
    assert provider.healthcheck_calls == 0


def test_lm_studio_connection_endpoint_returns_current_runtime_config(tmp_path) -> None:
    provider = HealthProvider(message="LM Studio is available")
    app = create_app(config=build_config(), provider=provider, storage_root=tmp_path)
    client = TestClient(app)

    response = client.get("/providers/lm-studio/connection")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "lm_studio",
        "host": "localhost",
        "port": 1234,
        "base_url": "http://localhost:1234/v1",
        "status": "available",
        "message": "LM Studio is available",
        "default_model": "local-model",
        "embedding_model": "local-model",
        "available_models": [],
    }
    assert provider.healthcheck_calls == 1


def test_lm_studio_connection_endpoint_updates_runtime_config(monkeypatch, tmp_path) -> None:
    built_base_urls: list[str] = []

    def fake_build_provider_runtime(config, provider=None):
        built_base_urls.append(config.lm_studio_base_url)
        registry = ProviderRegistry(
            providers={ProviderName.LM_STUDIO: provider or HealthProvider(message="Updated LM Studio is available")},
            enabled_providers=(ProviderName.LM_STUDIO,),
        )
        return ProviderRuntime(
            registry=registry,
            active_provider=registry.enforced_provider(ProviderName.LM_STUDIO),
        )

    monkeypatch.setattr("backend.app.api.health.build_provider_runtime", fake_build_provider_runtime)
    app = create_app(config=build_config(), provider=HealthProvider(), storage_root=tmp_path)
    app.state.generation_orchestrator = object()
    app.state.rag_generation_orchestrator = object()
    app.state.generation_dispatcher = object()
    client = TestClient(app)

    response = client.put("/providers/lm-studio/connection", json={"host": "192.168.1.42", "port": 1234})

    assert response.status_code == 200
    assert response.json()["base_url"] == "http://192.168.1.42:1234/v1"
    assert response.json()["host"] == "192.168.1.42"
    assert response.json()["port"] == 1234
    assert response.json()["message"] == "Updated LM Studio is available"
    assert built_base_urls == ["http://192.168.1.42:1234/v1"]
    assert app.state.config.lm_studio_base_url == "http://192.168.1.42:1234/v1"
    assert not hasattr(app.state, "generation_orchestrator")
    assert not hasattr(app.state, "rag_generation_orchestrator")
    assert not hasattr(app.state, "generation_dispatcher")


def test_lm_studio_connection_endpoint_rejects_non_host_values(tmp_path) -> None:
    app = create_app(config=build_config(), provider=HealthProvider(), storage_root=tmp_path)
    client = TestClient(app)

    response = client.put("/providers/lm-studio/connection", json={"host": "http://192.168.1.42/v1", "port": 1234})

    assert response.status_code == 422


def test_backend_health_propagates_request_id_into_response_and_logs(caplog) -> None:
    app = create_app(config=build_config(), provider=StubProvider())
    client = TestClient(app)
    records: list[logging.LogRecord] = []

    class CollectHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = CollectHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        with caplog.at_level(logging.INFO):
            response = client.get("/health", headers={"X-Request-ID": "req-123"})
    finally:
        root_logger.removeHandler(handler)

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert any(getattr(record, "correlation_id", None) == "req-123" for record in records)
