import json
import socket
from urllib.error import URLError

import pytest

from backend.app.domain.errors import LLMConnectionError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.llm.lm_studio import LMStudioClient
from backend.app.llm.retry import RetryPolicy


class FakeHTTPResponse:
    """Minimal context-manager response used to stub urllib calls."""

    def __init__(self, payload: bytes | dict[str, object]) -> None:
        self._payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        """Return the prepared raw response payload."""

        return self._payload

    def __enter__(self) -> "FakeHTTPResponse":
        """Return the response for context-manager usage."""

        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Propagate exceptions raised inside the context manager."""

        return False


def build_client() -> LMStudioClient:
    return LMStudioClient(
        base_url="http://localhost:1234/v1",
        default_model="local-model",
        timeout_seconds=7,
        retry_policy=RetryPolicy(
            max_retries=2,
            base_backoff_seconds=0.0,
            backoff_multiplier=1.0,
        ),
    )


def test_healthcheck_returns_available_status_for_valid_models_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "data": [
                    {"id": "local-model"},
                    {"id": "backup-model"},
                ]
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    status = build_client().healthcheck()

    assert status.status == "available"
    assert status.message == "LM Studio is available"
    assert captured["url"] == "http://localhost:1234/v1/models"
    assert captured["timeout"] == 7


def test_healthcheck_raises_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise socket.timeout("timed out")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMTimeoutError, match="timed out"):
        build_client().healthcheck()


def test_healthcheck_raises_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMConnectionError, match="refused"):
        build_client().healthcheck()


def test_healthcheck_raises_malformed_response_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse({"unexpected": []})

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="healthcheck"):
        build_client().healthcheck()
