from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.domain.errors import LLMConnectionError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import ProviderHealthStatus
from backend.app.llm.registry import ProviderName
from backend.app.main import create_app


class HealthyProvider:
    """Provider test double that reports a healthy LM Studio connection."""

    def healthcheck(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(status="available", message="LM Studio is available")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by LM Studio health tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by LM Studio health tests")


class FailingProvider:
    """Provider test double that raises one configured healthcheck error."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def healthcheck(self):
        raise self._error

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by LM Studio health tests")

    def embed(self, request):
        raise AssertionError("embed should not be called by LM Studio health tests")


def build_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
    )


def build_disabled_lm_studio_config() -> AppConfig:
    return AppConfig(
        lm_studio_base_url="http://localhost:1234/v1",
        lm_studio_model="local-model",
        log_format="%(levelname)s:%(message)s",
        providers_enabled=(ProviderName.OLLAMA,),
        default_provider=ProviderName.LM_STUDIO,
    )


def test_lm_studio_health_endpoint_returns_provider_status_and_default_model() -> None:
    app = create_app(config=build_config(), provider=HealthyProvider())
    client = TestClient(app)

    response = client.get("/health/lm-studio")

    assert response.status_code == 200
    assert response.json() == {
        "status": "available",
        "message": "LM Studio is available",
        "default_model": "local-model",
    }


def test_lm_studio_health_endpoint_reports_disabled_provider_without_calling_provider() -> None:
    provider = HealthyProvider()
    app = create_app(config=build_disabled_lm_studio_config(), provider=provider)
    client = TestClient(app)

    response = client.get("/health/lm-studio")

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "message": "Provider 'lm_studio' is disabled by PROVIDERS_ENABLED",
        "default_model": "local-model",
    }


def test_lm_studio_health_endpoint_maps_timeout_to_gateway_timeout() -> None:
    app = create_app(config=build_config(), provider=FailingProvider(LLMTimeoutError("LM Studio timed out")))
    client = TestClient(app)

    response = client.get("/health/lm-studio")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "llm_timeout_error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_lm_studio_health_endpoint_maps_connection_failure_to_service_unavailable() -> None:
    app = create_app(config=build_config(), provider=FailingProvider(LLMConnectionError("LM Studio unavailable")))
    client = TestClient(app)

    response = client.get("/health/lm-studio")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_connection_error"


def test_lm_studio_health_endpoint_maps_malformed_response_to_bad_gateway() -> None:
    app = create_app(
        config=build_config(),
        provider=FailingProvider(LLMResponseFormatError("LM Studio returned malformed response")),
    )
    client = TestClient(app)

    response = client.get("/health/lm-studio")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_response_format_error"
