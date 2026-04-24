import logging

from fastapi.testclient import TestClient

from backend.app.core.config import AppConfig
from backend.app.main import create_app


class StubProvider:
    """Test double for API health checks."""

    def healthcheck(self):
        raise AssertionError("LM Studio healthcheck should not be called by /health")

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


def test_backend_health_endpoint_returns_backend_status_and_basic_config_info() -> None:
    app = create_app(config=build_config(), provider=StubProvider())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "default_model": "local-model",
        "generation_modes": ["direct", "single_question_regen"],
    }
    assert response.headers["X-Request-ID"]


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
