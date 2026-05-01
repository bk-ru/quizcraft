import io
import json
import socket
from urllib.error import HTTPError
from urllib.error import URLError

import pytest

from backend.app.domain.errors import LLMConnectionError
from backend.app.domain.errors import LLMRequestError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMServerError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.llm.external_api import ExternalAPIClient
from backend.app.llm.retry import RetryPolicy


class FakeHTTPResponse:
    """Minimal context-manager response used to stub urllib calls."""

    def __init__(self, payload: bytes | dict[str, object]) -> None:
        self._payload = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def read(self) -> bytes:
        """Return the prepared raw response payload."""

        return self._payload

    def __enter__(self) -> "FakeHTTPResponse":
        """Return the response for context-manager usage."""

        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Propagate exceptions raised inside the context manager."""

        return False


def build_client(max_retries: int = 2, api_key: str | None = "test-token") -> ExternalAPIClient:
    return ExternalAPIClient(
        base_url="https://api.example.test/v1",
        api_key=api_key,
        default_model="external-quiz-model",
        default_embedding_model="external-embed-model",
        timeout_seconds=9,
        retry_policy=RetryPolicy(
            max_retries=max_retries,
            base_backoff_seconds=0.0,
            backoff_multiplier=1.0,
        ),
    )


def build_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        system_prompt="Сформируй квиз и верни JSON.",
        user_prompt="Документ: Москва — столица России.",
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


def test_healthcheck_uses_models_endpoint_and_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["authorization"] = request.get_header("Authorization")
        return FakeHTTPResponse({"data": [{"id": "external-quiz-model"}]})

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    status = build_client().healthcheck()

    assert status.status == "available"
    assert status.message == "External API is available"
    assert captured == {
        "url": "https://api.example.test/v1/models",
        "timeout": 9,
        "authorization": "Bearer test-token",
    }


def test_healthcheck_allows_missing_api_key_for_openai_compatible_local_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        return FakeHTTPResponse({"data": []})

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    status = build_client(api_key=None).healthcheck()

    assert status.status == "available"
    assert captured["authorization"] is None


def test_generate_structured_posts_json_schema_and_preserves_cyrillic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.get_header("Authorization")
        return FakeHTTPResponse(
            {
                "model": "external-quiz-model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"questions": [{"prompt": "Что является столицей России?"}]},
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    response = build_client().generate_structured(build_request())

    assert response.model_name == "external-quiz-model"
    assert response.content == {"questions": [{"prompt": "Что является столицей России?"}]}
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-token"
    assert captured["payload"] == {
        "model": "external-quiz-model",
        "messages": [
            {"role": "system", "content": "Сформируй квиз и верни JSON."},
            {"role": "user", "content": "Документ: Москва — столица России."},
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


def test_generate_structured_allows_explicit_model(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    request = build_request()
    request = StructuredGenerationRequest(
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        schema_name=request.schema_name,
        schema=request.schema,
        inference_parameters=request.inference_parameters,
        model_name="external-precise-model",
    )

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "external-precise-model",
                "choices": [{"message": {"content": json.dumps({"questions": [{"prompt": "Вопрос?"}]})}}],
            }
        )

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    response = build_client().generate_structured(request)

    assert response.model_name == "external-precise-model"
    assert captured["payload"]["model"] == "external-precise-model"


def test_embed_posts_openai_compatible_batch_and_preserves_cyrillic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "external-embed-model",
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    response = build_client().embed(
        EmbeddingRequest(texts=("Москва — столица России.", "Привет, мир!"))
    )

    assert response.model_name == "external-embed-model"
    assert response.vectors == ((0.1, 0.2), (0.3, 0.4))
    assert captured["url"] == "https://api.example.test/v1/embeddings"
    assert captured["payload"] == {
        "model": "external-embed-model",
        "input": ["Москва — столица России.", "Привет, мир!"],
    }


def test_generate_structured_retries_timeout_errors_and_raises_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise socket.timeout("timed out")

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMTimeoutError, match="timed out"):
        build_client(max_retries=2).generate_structured(build_request())

    assert call_count == 3


def test_embed_retries_server_errors_and_raises_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise HTTPError(
            url="https://api.example.test/v1/embeddings",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"unavailable"}'),
        )

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMServerError, match="503"):
        build_client(max_retries=2).embed(EmbeddingRequest(texts=("Москва",)))

    assert call_count == 3


def test_request_error_maps_to_controlled_error_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise HTTPError(
            url="https://api.example.test/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"bad token"}'),
        )

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMRequestError, match="401"):
        build_client(max_retries=2).generate_structured(build_request())

    assert call_count == 1


def test_connection_error_maps_to_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMConnectionError, match="refused"):
        build_client(max_retries=0).healthcheck()


def test_invalid_json_response_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(b"{broken-json")

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="invalid JSON"):
        build_client().generate_structured(build_request())


def test_malformed_structured_response_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse({"model": "external-quiz-model", "choices": [{"message": {"content": "not-json"}}]})

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="structured response"):
        build_client().generate_structured(build_request())


def test_malformed_embeddings_response_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "model": "external-embed-model",
                "data": [{"index": 0, "embedding": [0.1]}, {"index": 1, "embedding": "bad"}],
            }
        )

    monkeypatch.setattr("backend.app.llm.external_api.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="embeddings response"):
        build_client().embed(EmbeddingRequest(texts=("Москва", "Санкт-Петербург")))
