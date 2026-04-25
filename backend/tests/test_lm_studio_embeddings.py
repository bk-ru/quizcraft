import io
import json
import socket
from urllib.error import HTTPError

import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMServerError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import EmbeddingRequest
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


def build_client(max_retries: int = 2) -> LMStudioClient:
    return LMStudioClient(
        base_url="http://localhost:1234/v1",
        default_model="local-embed",
        timeout_seconds=7,
        retry_policy=RetryPolicy(
            max_retries=max_retries,
            base_backoff_seconds=0.0,
            backoff_multiplier=1.0,
        ),
    )


def test_embed_posts_input_payload_and_returns_vectors_for_cyrillic_texts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "model": "local-embed",
                "data": [
                    {"embedding": [0.1, 0.2, 0.3], "index": 0},
                    {"embedding": [0.4, 0.5, 0.6], "index": 1},
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    response = build_client().embed(
        EmbeddingRequest(texts=("Москва — столица России.", "Привет, мир!"))
    )

    assert captured["url"] == "http://localhost:1234/v1/embeddings"
    assert captured["timeout"] == 7
    assert captured["payload"] == {
        "model": "local-embed",
        "input": ["Москва — столица России.", "Привет, мир!"],
    }
    assert response.model_name == "local-embed"
    assert response.vectors == ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))


def test_embed_uses_request_model_when_overriding_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "alt-embed",
                "data": [{"embedding": [1.0, 2.0], "index": 0}],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    response = build_client().embed(
        EmbeddingRequest(texts=("Россия",), model_name="alt-embed")
    )

    assert captured["payload"]["model"] == "alt-embed"
    assert response.model_name == "alt-embed"


def test_embed_sorts_response_items_by_index(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "model": "local-embed",
                "data": [
                    {"embedding": [0.4, 0.5], "index": 1},
                    {"embedding": [0.1, 0.2], "index": 0},
                ],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    response = build_client().embed(
        EmbeddingRequest(texts=("Привет", "Мир"))
    )

    assert response.vectors == ((0.1, 0.2), (0.4, 0.5))


def test_embed_retries_timeout_errors_and_raises_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise socket.timeout("timed out")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMTimeoutError, match="timed out"):
        build_client(max_retries=2).embed(EmbeddingRequest(texts=("Москва",)))

    assert call_count == 3


def test_embed_retries_server_errors_and_raises_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise HTTPError(
            url="http://localhost:1234/v1/embeddings",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"unavailable"}'),
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMServerError, match="503"):
        build_client(max_retries=2).embed(EmbeddingRequest(texts=("Москва",)))

    assert call_count == 3


def test_embed_raises_response_format_error_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(b"{broken-json")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="invalid JSON"):
        build_client().embed(EmbeddingRequest(texts=("Москва",)))


def test_embed_raises_response_format_error_for_missing_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse({"model": "local-embed"})

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="embeddings response"):
        build_client().embed(EmbeddingRequest(texts=("Москва",)))


def test_embed_raises_response_format_error_for_count_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "model": "local-embed",
                "data": [{"embedding": [0.1, 0.2], "index": 0}],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="embeddings response"):
        build_client().embed(EmbeddingRequest(texts=("Привет", "Мир")))


def test_embed_raises_response_format_error_for_non_numeric_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "model": "local-embed",
                "data": [{"embedding": [0.1, "bad"], "index": 0}],
            }
        )

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="embeddings response"):
        build_client().embed(EmbeddingRequest(texts=("Москва",)))


def test_embedding_request_rejects_empty_texts() -> None:
    with pytest.raises(DomainValidationError, match="at least one entry"):
        EmbeddingRequest(texts=())


def test_embedding_request_rejects_non_string_text() -> None:
    with pytest.raises(DomainValidationError, match="must be a string"):
        EmbeddingRequest(texts=(123,))  # type: ignore[arg-type]


def test_embedding_request_rejects_blank_text() -> None:
    with pytest.raises(DomainValidationError, match="must not be empty"):
        EmbeddingRequest(texts=("   ",))


def test_embedding_request_rejects_blank_model_name() -> None:
    with pytest.raises(DomainValidationError, match="model_name"):
        EmbeddingRequest(texts=("Москва",), model_name="   ")


def test_embed_does_not_send_request_when_construction_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request, timeout):
        raise AssertionError("urlopen should not be called when validation fails")

    monkeypatch.setattr("backend.app.llm.lm_studio.urlopen", fake_urlopen)

    with pytest.raises(DomainValidationError):
        EmbeddingRequest(texts=())
