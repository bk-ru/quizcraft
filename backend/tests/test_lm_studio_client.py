import io
import json
import logging
import socket
from urllib.error import HTTPError

import pytest

from backend.app.domain.errors import LLMRequestError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMServerError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.llm.lm_studio import LMStudioClient
from backend.app.llm.retry import RetryPolicy


class FakeHTTPResponse:
    """Минимальный ответ context manager, используемый для stub вызовов urllib."""

    def __init__(self, payload: bytes | dict[str, object]) -> None:
        self._payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        """Вернуть подготовленный raw payload ответа."""

        return self._payload

    def __enter__(self) -> "FakeHTTPResponse":
        """Вернуть ответ для использования context manager."""

        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Пробросить исключения, вызванные внутри context manager."""

        return False


def build_client(max_retries: int = 2) -> LMStudioClient:
    return LMStudioClient(
        base_url="http://localhost:1234/v1",
        default_model="local-model",
        timeout_seconds=7,
        retry_policy=RetryPolicy(
            max_retries=max_retries,
            base_backoff_seconds=0.0,
            backoff_multiplier=1.0,
        ),
    )


def build_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        system_prompt="You turn source text into a quiz.",
        user_prompt="Generate one question in JSON.",
        schema_name="quiz_payload",
        schema={
            "type": "object",
            "required": ["questions"],
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        inference_parameters={"temperature": 0.2, "max_tokens": 256},
    )


def test_client_posts_schema_and_returns_structured_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "model": "local-model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"questions": [{"prompt": "Question 1"}]})
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    response = build_client().generate_structured(build_request())

    assert response.model_name == "local-model"
    assert response.content == {"questions": [{"prompt": "Question 1"}]}
    assert captured["timeout"] == 7
    assert captured["payload"] == {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "You turn source text into a quiz."},
            {"role": "user", "content": "Generate one question in JSON."},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "quiz_payload",
                "schema": build_request().schema,
                "strict": True,
            },
        },
        "temperature": 0.2,
        "max_tokens": 256,
    }


def test_client_logs_safe_request_and_response_summary(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "model": "local-model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"questions": [{"prompt": "Question 1"}]})
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with caplog.at_level(logging.INFO, logger="backend.app.llm.lm_studio"):
        build_client().generate_structured(build_request())

    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "Sending LM Studio request path=/chat/completions" in rendered
    assert "Received LM Studio response path=/chat/completions" in rendered
    assert "schema_name" in rendered
    assert "user_prompt_preview" in rendered
    assert "You turn source text into a quiz." not in rendered


def test_client_includes_upstream_error_body_for_request_errors(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        raise HTTPError(
            url="http://localhost:1234/v1/chat/completions",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"model does not support json_schema"}'),
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with caplog.at_level(logging.WARNING, logger="backend.app.llm.lm_studio"):
        with pytest.raises(LLMRequestError, match="model does not support json_schema"):
            build_client(max_retries=0).generate_structured(build_request())

    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "LM Studio HTTP error path=/chat/completions status=400" in rendered
    assert "model does not support json_schema" in rendered


def test_client_retries_timeout_errors_and_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise socket.timeout("timed out")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMTimeoutError, match="timed out") as error_info:
        build_client(max_retries=2).generate_structured(build_request())

    assert call_count == 3
    assert error_info.value.diagnostic["path"] == "/chat/completions"
    assert error_info.value.diagnostic["reason"] == "timeout"


def test_client_raises_controlled_error_for_invalid_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        return FakeHTTPResponse(b"{broken-json")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="invalid JSON"):
        build_client().generate_structured(build_request())

    assert call_count == 1


def test_client_retries_server_errors_and_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise HTTPError(
            url="http://localhost:1234/v1/chat/completions",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"unavailable"}'),
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMServerError, match="503"):
        build_client(max_retries=2).generate_structured(build_request())

    assert call_count == 3


def test_client_raises_controlled_error_for_malformed_structured_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        return FakeHTTPResponse(
            {
                "model": "local-model",
                "choices": [
                    {
                        "message": {
                            "content": "not-json"
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="structured response") as error_info:
        build_client().generate_structured(build_request())

    assert call_count == 1
    assert error_info.value.diagnostic["reason"] == "message_content_invalid_json"
    assert error_info.value.diagnostic["content_preview"] == "not-json"
    assert error_info.value.diagnostic["response_keys"] == ["choices", "model"]


def test_healthcheck_malformed_response_includes_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(b"{broken-json")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="healthcheck") as error_info:
        build_client(max_retries=0).healthcheck()

    assert error_info.value.diagnostic["path"] == "/models"
    assert error_info.value.diagnostic["reason"] == "invalid_json"
    assert error_info.value.diagnostic["raw_response_preview"] == "{broken-json"


def test_healthcheck_timeout_includes_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise socket.timeout("timed out")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMTimeoutError, match="timed out") as error_info:
        build_client(max_retries=0).healthcheck()

    assert error_info.value.diagnostic["path"] == "/models"
    assert error_info.value.diagnostic["reason"] == "timeout"


def test_client_summarizes_lm_studio_response_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "model": "local-model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"questions": [{"prompt": "Question 1"}]})
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                "stats": {"tokens_per_second": 12.345, "time_to_first_token": 0.456, "stop_reason": "eosFound"},
                "model_info": {"context_length": 4096, "quant": "Q4_K_M", "arch": "llama"},
                "runtime": {"name": "llama.cpp", "version": "1.2.3"},
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    response = build_client().generate_structured(build_request())

    assert response.provider_metadata == {
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "stats": {"tokens_per_second": 12.345, "time_to_first_token": 0.456, "stop_reason": "eosFound"},
        "model_info": {"context_length": 4096, "quant": "Q4_K_M", "arch": "llama"},
        "runtime": {"name": "llama.cpp", "version": "1.2.3"},
    }
