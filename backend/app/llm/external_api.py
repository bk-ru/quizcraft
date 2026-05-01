"""External OpenAI-compatible API client for structured chat and embeddings requests."""

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


class ExternalAPIClient(LLMProvider):
    """External provider backed by the OpenAI-compatible HTTP API contract."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
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
        self._api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        self._default_model = default_model.strip()
        self._default_embedding_model = default_embedding_model.strip()
        self._timeout_seconds = timeout_seconds
        self._retrying_caller = retrying_caller or RetryingCaller(retry_policy or RetryPolicy())

    def healthcheck(self) -> ProviderHealthStatus:
        """Check whether the external OpenAI-compatible API is reachable."""

        request = Request(
            url=f"{self._base_url}/models",
            headers=self._build_headers(),
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
            raise LLMTimeoutError("External API request timed out") from error
        except socket.timeout as error:
            raise LLMTimeoutError("External API request timed out") from error

        try:
            response_payload = json.loads(raw_response)
        except JSONDecodeError as error:
            raise LLMResponseFormatError("External API healthcheck returned malformed response") from error

        if not isinstance(response_payload, dict):
            raise LLMResponseFormatError("External API healthcheck returned malformed response")
        models = response_payload.get("data")
        if not isinstance(models, list):
            raise LLMResponseFormatError("External API healthcheck returned malformed response")

        logger.info("External API healthcheck succeeded")
        return ProviderHealthStatus(
            status="available",
            message="External API is available",
        )

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Submit a structured generation request to the external API."""

        return self._retrying_caller.execute(lambda: self._generate_structured_once(request))

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings through the external API embeddings endpoint."""

        return self._retrying_caller.execute(lambda: self._embed_once(request))

    def _generate_structured_once(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Perform one chat-completion request without retry orchestration."""

        payload = self._build_payload(request)
        response_payload = self._post_json("/chat/completions", payload)
        return self._extract_structured_response(response_payload)

    def _embed_once(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Perform one embeddings request without retry orchestration."""

        payload = self._build_embeddings_payload(request)
        response_payload = self._post_json("/embeddings", payload)
        return self._extract_embeddings_response(response_payload, expected_count=len(request.texts))

    def _build_payload(self, request: StructuredGenerationRequest) -> dict[str, object]:
        """Build the OpenAI-compatible chat-completions payload."""

        payload: dict[str, object] = {
            "model": request.model_name or self._default_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "schema": request.schema,
                    "strict": True,
                },
            },
        }
        payload.update(request.inference_parameters)
        return payload

    def _build_embeddings_payload(self, request: EmbeddingRequest) -> dict[str, object]:
        """Build the OpenAI-compatible embeddings payload."""

        return {
            "model": request.model_name or self._default_embedding_model,
            "input": list(request.texts),
        }

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        """POST a JSON payload to one of the external OpenAI-compatible endpoints."""

        request = Request(
            url=f"{self._base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._build_headers({"Content-Type": "application/json"}),
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
            raise LLMTimeoutError("External API request timed out") from error
        except socket.timeout as error:
            raise LLMTimeoutError("External API request timed out") from error

        try:
            parsed_response = json.loads(raw_response)
        except JSONDecodeError as error:
            raise LLMResponseFormatError("External API returned invalid JSON") from error

        if not isinstance(parsed_response, dict):
            raise LLMResponseFormatError("External API returned invalid JSON")
        return parsed_response

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers without requiring a committed API key."""

        headers = {"Accept": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _extract_structured_response(
        self,
        response_payload: dict[str, object],
    ) -> StructuredGenerationResponse:
        """Validate and unwrap the structured response content."""

        model_name = response_payload.get("model")
        if not isinstance(model_name, str) or not model_name:
            raise LLMResponseFormatError("External API returned a malformed structured response")

        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseFormatError("External API returned a malformed structured response")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMResponseFormatError("External API returned a malformed structured response")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LLMResponseFormatError("External API returned a malformed structured response")

        content = message.get("content")
        if isinstance(content, dict):
            structured_content = content
        elif isinstance(content, str) and content.strip():
            try:
                structured_content = json.loads(content)
            except JSONDecodeError as error:
                raise LLMResponseFormatError("External API returned a malformed structured response") from error
        else:
            raise LLMResponseFormatError("External API returned a malformed structured response")

        if not isinstance(structured_content, dict):
            raise LLMResponseFormatError("External API returned a malformed structured response")

        logger.info("Received structured response from external API model %s", model_name)
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
        """Validate and unwrap the embeddings response payload."""

        model_name = response_payload.get("model")
        if not isinstance(model_name, str) or not model_name:
            raise LLMResponseFormatError("External API returned a malformed embeddings response")

        data = response_payload.get("data")
        if not isinstance(data, list) or not data:
            raise LLMResponseFormatError("External API returned a malformed embeddings response")

        ordered_vectors = self._sort_embedding_items(data)
        if len(ordered_vectors) != expected_count:
            raise LLMResponseFormatError("External API returned a malformed embeddings response")

        logger.info("Received embeddings response from external API model %s", model_name)
        return EmbeddingResponse(
            model_name=model_name,
            vectors=tuple(ordered_vectors),
        )

    @staticmethod
    def _sort_embedding_items(data: list[object]) -> list[tuple[float, ...]]:
        """Convert raw embedding items into ordered tuples of floats."""

        indexed_vectors: list[tuple[int, tuple[float, ...]]] = []
        for fallback_index, item in enumerate(data):
            if not isinstance(item, dict):
                raise LLMResponseFormatError("External API returned a malformed embeddings response")
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise LLMResponseFormatError("External API returned a malformed embeddings response")
            vector: list[float] = []
            for value in embedding:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise LLMResponseFormatError("External API returned a malformed embeddings response")
                vector.append(float(value))
            raw_index = item.get("index", fallback_index)
            if isinstance(raw_index, bool) or not isinstance(raw_index, int):
                raise LLMResponseFormatError("External API returned a malformed embeddings response")
            indexed_vectors.append((raw_index, tuple(vector)))
        indexed_vectors.sort(key=lambda pair: pair[0])
        return [vector for _, vector in indexed_vectors]

    def _map_http_error(self, error: HTTPError):
        """Convert HTTP status failures into controlled domain errors."""

        if error.code >= 500:
            return LLMServerError(error.code, f"External API returned server error {error.code}")
        return LLMRequestError(error.code, f"External API returned request error {error.code}")

    def _map_url_error(self, error: URLError):
        """Convert URL transport failures into controlled domain errors."""

        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return LLMTimeoutError("External API request timed out")
        return LLMConnectionError(f"External API request failed: {error.reason}")
