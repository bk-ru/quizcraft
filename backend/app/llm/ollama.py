"""Ollama client for structured chat and embeddings requests."""

from __future__ import annotations

import json
import logging
import socket
from json import JSONDecodeError
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

from backend.app.domain.errors import LLMConnectionError
from backend.app.domain.errors import LLMRequestError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMServerError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.llm.provider import LLMProvider
from backend.app.llm.retry import RetryPolicy
from backend.app.llm.retry import RetryingCaller

logger = logging.getLogger(__name__)


class OllamaClient(LLMProvider):
    """Ollama client backed by the native HTTP API."""

    def __init__(
        self,
        base_url: str,
        default_model: str,
        default_embedding_model: str,
        timeout_seconds: int,
        retry_policy: RetryPolicy | None = None,
        retrying_caller: RetryingCaller | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must be non-empty")
        if not default_model.strip():
            raise ValueError("default_model must be non-empty")
        if not default_embedding_model.strip():
            raise ValueError("default_embedding_model must be non-empty")
        self._base_url = base_url.strip().rstrip("/")
        self._default_model = default_model.strip()
        self._default_embedding_model = default_embedding_model.strip()
        self._timeout_seconds = timeout_seconds
        self._retrying_caller = retrying_caller or RetryingCaller(retry_policy or RetryPolicy())

    def healthcheck(self) -> ProviderHealthStatus:
        """Check whether the Ollama API is reachable."""

        request = Request(
            url=f"{self._base_url}/api/tags",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except HTTPError as error:
            raise self._map_http_error(error) from error
        except URLError as error:
            raise self._map_url_error(error) from error
        except TimeoutError as error:
            raise LLMTimeoutError("Ollama request timed out") from error
        except socket.timeout as error:
            raise LLMTimeoutError("Ollama request timed out") from error

        try:
            response_payload = json.loads(raw_response)
        except JSONDecodeError as error:
            raise LLMResponseFormatError("Ollama healthcheck returned malformed response") from error

        if not isinstance(response_payload, dict):
            raise LLMResponseFormatError("Ollama healthcheck returned malformed response")
        models = response_payload.get("models")
        if not isinstance(models, list):
            raise LLMResponseFormatError("Ollama healthcheck returned malformed response")

        logger.info("Ollama healthcheck succeeded")
        return ProviderHealthStatus(
            status="available",
            message="Ollama is available",
        )

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Submit a structured generation request to Ollama."""

        return self._retrying_caller.execute(lambda: self._generate_structured_once(request))

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings for one or more texts via Ollama."""

        return self._retrying_caller.execute(lambda: self._embed_once(request))

    def _generate_structured_once(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Perform one Ollama chat request without retry orchestration."""

        payload = self._build_payload(request)
        response_payload = self._post_json("/api/chat", payload)
        return self._extract_structured_response(response_payload)

    def _embed_once(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Perform one Ollama embeddings request without retry orchestration."""

        payload = self._build_embeddings_payload(request)
        response_payload = self._post_json("/api/embed", payload)
        return self._extract_embeddings_response(response_payload, expected_count=len(request.texts))

    def _build_payload(self, request: StructuredGenerationRequest) -> dict[str, object]:
        """Build the Ollama chat payload."""

        payload: dict[str, object] = {
            "model": request.model_name or self._default_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "format": request.schema,
        }
        if request.inference_parameters:
            payload["options"] = dict(request.inference_parameters)
        return payload

    def _build_embeddings_payload(self, request: EmbeddingRequest) -> dict[str, object]:
        """Build the Ollama embeddings payload."""

        return {
            "model": request.model_name or self._default_embedding_model,
            "input": list(request.texts),
        }

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        """POST a JSON payload to one of the Ollama endpoints."""

        request = Request(
            url=f"{self._base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except HTTPError as error:
            raise self._map_http_error(error) from error
        except URLError as error:
            raise self._map_url_error(error) from error
        except TimeoutError as error:
            raise LLMTimeoutError("Ollama request timed out") from error
        except socket.timeout as error:
            raise LLMTimeoutError("Ollama request timed out") from error

        try:
            parsed_response = json.loads(raw_response)
        except JSONDecodeError as error:
            raise LLMResponseFormatError("Ollama returned invalid JSON") from error

        if not isinstance(parsed_response, dict):
            raise LLMResponseFormatError("Ollama returned invalid JSON")
        return parsed_response

    def _extract_structured_response(
        self,
        response_payload: dict[str, object],
    ) -> StructuredGenerationResponse:
        """Validate and unwrap the Ollama structured response content."""

        model_name = response_payload.get("model")
        if not isinstance(model_name, str) or not model_name:
            raise LLMResponseFormatError("Ollama returned a malformed structured response")

        message = response_payload.get("message")
        if not isinstance(message, dict):
            raise LLMResponseFormatError("Ollama returned a malformed structured response")

        content = message.get("content")
        if isinstance(content, dict):
            structured_content = content
        elif isinstance(content, str) and content.strip():
            try:
                structured_content = json.loads(content)
            except JSONDecodeError as error:
                raise LLMResponseFormatError("Ollama returned a malformed structured response") from error
        else:
            raise LLMResponseFormatError("Ollama returned a malformed structured response")

        if not isinstance(structured_content, dict):
            raise LLMResponseFormatError("Ollama returned a malformed structured response")

        logger.info("Received structured response from Ollama model %s", model_name)
        return StructuredGenerationResponse(
            model_name=model_name,
            content=structured_content,
            raw_response=response_payload,
        )

    def _extract_embeddings_response(
        self,
        response_payload: dict[str, object],
        expected_count: int,
    ) -> EmbeddingResponse:
        """Validate and unwrap the Ollama embeddings response payload."""

        model_name = response_payload.get("model")
        if not isinstance(model_name, str) or not model_name:
            raise LLMResponseFormatError("Ollama returned a malformed embeddings response")

        embeddings = response_payload.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise LLMResponseFormatError("Ollama returned a malformed embeddings response")
        if len(embeddings) != expected_count:
            raise LLMResponseFormatError("Ollama returned a malformed embeddings response")

        vectors = tuple(self._coerce_embedding(embedding) for embedding in embeddings)
        logger.info("Received embeddings response from Ollama model %s", model_name)
        return EmbeddingResponse(
            model_name=model_name,
            vectors=vectors,
        )

    @staticmethod
    def _coerce_embedding(embedding: object) -> tuple[float, ...]:
        """Convert one raw embedding item into a tuple of floats."""

        if not isinstance(embedding, list) or not embedding:
            raise LLMResponseFormatError("Ollama returned a malformed embeddings response")
        vector: list[float] = []
        for value in embedding:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise LLMResponseFormatError("Ollama returned a malformed embeddings response")
            vector.append(float(value))
        return tuple(vector)

    def _map_http_error(self, error: HTTPError):
        """Convert HTTP status failures into controlled domain errors."""

        if error.code >= 500:
            return LLMServerError(error.code, f"Ollama returned server error {error.code}")
        return LLMRequestError(error.code, f"Ollama returned request error {error.code}")

    def _map_url_error(self, error: URLError):
        """Convert URL transport failures into controlled domain errors."""

        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return LLMTimeoutError("Ollama request timed out")
        return LLMConnectionError(f"Ollama request failed: {error.reason}")
