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
from backend.app.llm.ollama import OllamaClient
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


def build_client(max_retries: int = 2) -> OllamaClient:
    return OllamaClient(
        base_url="http://localhost:11434",
        default_model="qwen2.5:7b",
        default_embedding_model="nomic-embed-text",
        timeout_seconds=7,
        retry_policy=RetryPolicy(
            max_retries=max_retries,
            base_backoff_seconds=0.0,
            backoff_multiplier=1.0,
        ),
    )


def build_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        system_prompt="Создай тест по документу и верни JSON.",
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
        inference_parameters={"temperature": 0.2, "num_predict": 256},
    )


def test_healthcheck_returns_available_status(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeHTTPResponse({"models": [{"name": "qwen2.5:7b"}]})

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    status = build_client().healthcheck()

    assert status.status == "available"
    assert status.message == "Ollama is available"
    assert captured == {"url": "http://localhost:11434/api/tags", "timeout": 7}


def test_generate_structured_posts_schema_and_preserves_cyrillic(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "model": "qwen2.5:7b",
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"questions": [{"prompt": "Что является столицей России?"}]}),
                },
            }
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    response = build_client().generate_structured(build_request())

    assert response.model_name == "qwen2.5:7b"
    assert response.content == {"questions": [{"prompt": "Что является столицей России?"}]}
    assert captured["timeout"] == 7
    assert captured["payload"] == {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "Создай тест по документу и верни JSON."},
            {"role": "user", "content": "Документ: Москва — столица России."},
        ],
        "stream": False,
        "format": build_request().schema,
        "options": {"temperature": 0.2, "num_predict": 256},
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
        model_name="mistral:7b",
    )

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "mistral:7b",
                "message": {"content": json.dumps({"questions": [{"prompt": "Вопрос?"}]})},
            }
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    response = build_client().generate_structured(request)

    assert response.model_name == "mistral:7b"
    assert captured["payload"]["model"] == "mistral:7b"


def test_embed_posts_batch_and_preserves_cyrillic(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "nomic-embed-text",
                "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            }
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    response = build_client().embed(EmbeddingRequest(texts=("Москва — столица России.", "Привет, мир!")))

    assert response.model_name == "nomic-embed-text"
    assert response.vectors == ((0.1, 0.2), (0.3, 0.4))
    assert captured["payload"] == {
        "model": "nomic-embed-text",
        "input": ["Москва — столица России.", "Привет, мир!"],
    }


def test_embed_allows_explicit_model(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "model": "bge-m3",
                "embeddings": [[1, 2, 3]],
            }
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    response = build_client().embed(EmbeddingRequest(texts=("Россия",), model_name="bge-m3"))

    assert response.model_name == "bge-m3"
    assert response.vectors == ((1.0, 2.0, 3.0),)
    assert captured["payload"]["model"] == "bge-m3"


def test_generate_structured_retries_timeout_errors_and_raises_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise socket.timeout("timed out")

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMTimeoutError, match="timed out"):
        build_client(max_retries=2).generate_structured(build_request())

    assert call_count == 3


def test_embed_retries_server_errors_and_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise HTTPError(
            url="http://localhost:11434/api/embed",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"unavailable"}'),
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMServerError, match="503"):
        build_client(max_retries=2).embed(EmbeddingRequest(texts=("Москва",)))

    assert call_count == 3


def test_request_error_maps_to_controlled_error_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_urlopen(request, timeout):
        nonlocal call_count
        call_count += 1
        raise HTTPError(
            url="http://localhost:11434/api/chat",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"bad request"}'),
        )

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMRequestError, match="400"):
        build_client(max_retries=2).generate_structured(build_request())

    assert call_count == 1


def test_connection_error_maps_to_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMConnectionError, match="refused"):
        build_client(max_retries=0).healthcheck()


def test_invalid_json_response_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(b"{broken-json")

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="invalid JSON"):
        build_client().generate_structured(build_request())


def test_malformed_structured_response_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse({"model": "qwen2.5:7b", "message": {"content": "not-json"}})

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="structured response"):
        build_client().generate_structured(build_request())


def test_malformed_embeddings_response_raises_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse({"model": "nomic-embed-text", "embeddings": [[0.1], [0.2]]})

    monkeypatch.setattr("backend.app.llm.ollama.urlopen", fake_urlopen)

    with pytest.raises(LLMResponseFormatError, match="embeddings response"):
        build_client().embed(EmbeddingRequest(texts=("Москва",)))
