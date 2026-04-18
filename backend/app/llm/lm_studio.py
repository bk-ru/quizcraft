"""LM Studio client for structured chat-completion requests."""

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
from backend.app.domain.errors import UnsupportedProviderCapabilityError
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.domain.models import ProviderHealthStatus
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.llm.provider import LLMProvider
from backend.app.llm.retry import RetryPolicy
from backend.app.llm.retry import RetryingCaller

logger = logging.getLogger(__name__)


class LMStudioClient(LLMProvider):
    """Structured LM Studio client backed by the OpenAI-compatible chat API."""

    def __init__(
        self,
        base_url: str,
        default_model: str,
        timeout_seconds: int,
        retry_policy: RetryPolicy | None = None,
        retrying_caller: RetryingCaller | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds
        self._retrying_caller = retrying_caller or RetryingCaller(retry_policy or RetryPolicy())

    def healthcheck(self) -> ProviderHealthStatus:
        """Check whether the LM Studio OpenAI-compatible API is reachable."""

        request = Request(
            url=f"{self._base_url}/models",
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
            raise LLMTimeoutError("LM Studio request timed out") from error
        except socket.timeout as error:
            raise LLMTimeoutError("LM Studio request timed out") from error

        try:
            response_payload = json.loads(raw_response)
        except JSONDecodeError as error:
            raise LLMResponseFormatError("LM Studio healthcheck returned malformed response") from error

        if not isinstance(response_payload, dict):
            raise LLMResponseFormatError("LM Studio healthcheck returned malformed response")

        models = response_payload.get("data")
        if not isinstance(models, list):
            raise LLMResponseFormatError("LM Studio healthcheck returned malformed response")

        logger.info("LM Studio healthcheck succeeded")
        return ProviderHealthStatus(
            status="available",
            message="LM Studio is available",
        )

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Submit a structured generation request to LM Studio."""

        return self._retrying_caller.execute(lambda: self._generate_structured_once(request))

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Raise a controlled placeholder until the embeddings stage lands."""

        raise UnsupportedProviderCapabilityError("LM Studio embeddings are not implemented in Batch 1")

    def _generate_structured_once(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Perform one chat-completion request without retry orchestration."""

        payload = self._build_payload(request)
        response_payload = self._post_json(payload)
        return self._extract_structured_response(response_payload)

    def _build_payload(self, request: StructuredGenerationRequest) -> dict[str, object]:
        """Build the LM Studio chat-completions payload."""

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

    def _post_json(self, payload: dict[str, object]) -> dict[str, object]:
        """POST a JSON payload to the LM Studio chat-completions endpoint."""

        request = Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
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
            raise LLMTimeoutError("LM Studio request timed out") from error
        except socket.timeout as error:
            raise LLMTimeoutError("LM Studio request timed out") from error

        try:
            parsed_response = json.loads(raw_response)
        except JSONDecodeError as error:
            raise LLMResponseFormatError("LM Studio returned invalid JSON") from error

        if not isinstance(parsed_response, dict):
            raise LLMResponseFormatError("LM Studio returned invalid JSON")
        return parsed_response

    def _extract_structured_response(
        self,
        response_payload: dict[str, object],
    ) -> StructuredGenerationResponse:
        """Validate and unwrap the structured response content."""

        model_name = response_payload.get("model")
        if not isinstance(model_name, str) or not model_name:
            raise LLMResponseFormatError("LM Studio returned a malformed structured response")

        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseFormatError("LM Studio returned a malformed structured response")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMResponseFormatError("LM Studio returned a malformed structured response")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LLMResponseFormatError("LM Studio returned a malformed structured response")

        content = message.get("content")
        if isinstance(content, dict):
            structured_content = content
        elif isinstance(content, str) and content.strip():
            try:
                structured_content = json.loads(content)
            except JSONDecodeError as error:
                raise LLMResponseFormatError("LM Studio returned a malformed structured response") from error
        else:
            raise LLMResponseFormatError("LM Studio returned a malformed structured response")

        if not isinstance(structured_content, dict):
            raise LLMResponseFormatError("LM Studio returned a malformed structured response")

        logger.info("Received structured response from LM Studio model %s", model_name)
        return StructuredGenerationResponse(
            model_name=model_name,
            content=structured_content,
            raw_response=response_payload,
        )

    def _map_http_error(self, error: HTTPError):
        """Convert HTTP status failures into controlled domain errors."""

        if error.code >= 500:
            return LLMServerError(error.code, f"LM Studio returned server error {error.code}")
        return LLMRequestError(error.code, f"LM Studio returned request error {error.code}")

    def _map_url_error(self, error: URLError):
        """Convert URL transport failures into controlled domain errors."""

        if isinstance(error.reason, TimeoutError | socket.timeout):
            return LLMTimeoutError("LM Studio request timed out")
        return LLMConnectionError(f"LM Studio request failed: {error.reason}")
