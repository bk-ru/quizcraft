"""Клиент LM Studio для структурированных chat-completion запросов."""

from __future__ import annotations

import json
import logging
import socket
from json import JSONDecodeError
from typing import Any
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

MAX_UPSTREAM_ERROR_BODY_CHARS = 4000
MAX_LOG_PREVIEW_CHARS = 500


class LMStudioClient(LLMProvider):
    """Структурированный клиент LM Studio на основе OpenAI-compatible chat API."""

    def __init__(
        self,
        base_url: str,
        default_model: str,
        timeout_seconds: int | None,
        default_embedding_model: str | None = None,
        retry_policy: RetryPolicy | None = None,
        retrying_caller: RetryingCaller | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._default_embedding_model = default_embedding_model or default_model
        self._timeout_seconds = timeout_seconds
        self._retrying_caller = retrying_caller or RetryingCaller(retry_policy or RetryPolicy())

    def healthcheck(self) -> ProviderHealthStatus:
        """Проверить доступность OpenAI-compatible API LM Studio."""

        request = Request(
            url=f"{self._base_url}/models",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except HTTPError as error:
            raise self._map_http_error(
                error,
                path="/models",
                request_summary={"method": "GET", "payload_keys": []},
            ) from error
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
        """Отправить структурированный запрос генерации в LM Studio."""

        return self._retrying_caller.execute(lambda: self._generate_structured_once(request))

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Сгенерировать embeddings для одного или нескольких текстов через embeddings endpoint LM Studio."""

        return self._retrying_caller.execute(lambda: self._embed_once(request))

    def _generate_structured_once(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Выполнить один chat-completion запрос без retry orchestration."""

        payload = self._build_payload(request)
        response_payload = self._post_json("/chat/completions", payload)
        return self._extract_structured_response(response_payload)

    def _embed_once(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Выполнить один embeddings запрос без retry orchestration."""

        payload = self._build_embeddings_payload(request)
        response_payload = self._post_json("/embeddings", payload)
        return self._extract_embeddings_response(response_payload, expected_count=len(request.texts))

    def _build_payload(self, request: StructuredGenerationRequest) -> dict[str, object]:
        """Сформировать payload chat-completions для LM Studio."""

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
        """Сформировать payload embeddings для LM Studio."""

        return {
            "model": request.model_name or self._default_embedding_model,
            "input": list(request.texts),
        }

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        """Отправить JSON payload методом POST в один из OpenAI-compatible endpoint'ов LM Studio."""

        request_summary = self._summarize_request_payload(path, payload)
        logger.info("Sending LM Studio request path=%s payload=%s", path, request_summary)
        request = Request(
            url=f"{self._base_url}{path}",
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
            raise self._map_http_error(error, path=path, request_summary=request_summary) from error
        except URLError as error:
            logger.warning("LM Studio transport error path=%s error=%s", path, error.reason)
            raise self._map_url_error(error) from error
        except TimeoutError as error:
            logger.warning("LM Studio request timed out path=%s", path)
            raise LLMTimeoutError("LM Studio request timed out") from error
        except socket.timeout as error:
            logger.warning("LM Studio request timed out path=%s", path)
            raise LLMTimeoutError("LM Studio request timed out") from error

        try:
            parsed_response = json.loads(raw_response)
        except JSONDecodeError as error:
            logger.warning(
                "LM Studio returned invalid JSON path=%s raw_response_preview=%s",
                path,
                _truncate(raw_response),
            )
            raise LLMResponseFormatError("LM Studio returned invalid JSON") from error

        if not isinstance(parsed_response, dict):
            raise LLMResponseFormatError("LM Studio returned invalid JSON")
        logger.info(
            "Received LM Studio response path=%s response=%s",
            path,
            self._summarize_response_payload(path, parsed_response, len(raw_response)),
        )
        return parsed_response

    def _extract_structured_response(
        self,
        response_payload: dict[str, object],
    ) -> StructuredGenerationResponse:
        """Проверить и извлечь содержимое структурированного ответа."""

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

    def _extract_embeddings_response(
        self,
        response_payload: dict[str, object],
        expected_count: int,
    ) -> EmbeddingResponse:
        """Проверить и извлечь payload ответа embeddings."""

        model_name = response_payload.get("model")
        if not isinstance(model_name, str) or not model_name:
            raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")

        data = response_payload.get("data")
        if not isinstance(data, list) or not data:
            raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")

        ordered_vectors = self._sort_embedding_items(data)

        if len(ordered_vectors) != expected_count:
            raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")

        logger.info("Received embeddings response from LM Studio model %s", model_name)
        return EmbeddingResponse(
            model_name=model_name,
            vectors=tuple(ordered_vectors),
        )

    @staticmethod
    def _sort_embedding_items(data: list[object]) -> list[tuple[float, ...]]:
        """Преобразовать raw элементы embedding в упорядоченные tuple из float."""

        indexed_vectors: list[tuple[int, tuple[float, ...]]] = []
        for fallback_index, item in enumerate(data):
            if not isinstance(item, dict):
                raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")
            vector: list[float] = []
            for value in embedding:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")
                vector.append(float(value))
            raw_index = item.get("index", fallback_index)
            if isinstance(raw_index, bool) or not isinstance(raw_index, int):
                raise LLMResponseFormatError("LM Studio returned a malformed embeddings response")
            indexed_vectors.append((raw_index, tuple(vector)))
        indexed_vectors.sort(key=lambda pair: pair[0])
        return [vector for _, vector in indexed_vectors]

    def _map_http_error(
        self,
        error: HTTPError,
        *,
        path: str,
        request_summary: dict[str, Any],
    ):
        """Преобразовать сбои HTTP-статуса в контролируемые доменные ошибки."""

        upstream_body = _read_http_error_body(error)
        upstream_body_preview = _truncate(upstream_body, MAX_UPSTREAM_ERROR_BODY_CHARS)
        logger.warning(
            "LM Studio HTTP error path=%s status=%s reason=%s request=%s response_body=%s",
            path,
            error.code,
            error.reason,
            request_summary,
            upstream_body_preview,
        )
        message_suffix = f": {upstream_body_preview}" if upstream_body_preview else ""
        if error.code >= 500:
            return LLMServerError(error.code, f"LM Studio returned server error {error.code}{message_suffix}")
        return LLMRequestError(error.code, f"LM Studio returned request error {error.code}{message_suffix}")

    def _map_url_error(self, error: URLError):
        """Преобразовать транспортные URL-сбои в контролируемые доменные ошибки."""

        if isinstance(error.reason, TimeoutError | socket.timeout):
            return LLMTimeoutError("LM Studio request timed out")
        return LLMConnectionError(f"LM Studio request failed: {error.reason}")

    @staticmethod
    def _summarize_request_payload(path: str, payload: dict[str, object]) -> dict[str, Any]:
        """Вернуть безопасную сводку исходящего payload без полного prompt/document text."""

        summary: dict[str, Any] = {
            "model": payload.get("model"),
            "payload_keys": sorted(payload),
        }
        if path == "/chat/completions":
            messages = payload.get("messages")
            if isinstance(messages, list):
                summary["message_count"] = len(messages)
                summary["message_roles"] = [
                    item.get("role")
                    for item in messages
                    if isinstance(item, dict)
                ]
                summary["message_chars"] = [
                    len(content)
                    for item in messages
                    if isinstance(item, dict) and isinstance((content := item.get("content")), str)
                ]
                user_messages = [
                    item.get("content")
                    for item in messages
                    if isinstance(item, dict)
                    and item.get("role") == "user"
                    and isinstance(item.get("content"), str)
                ]
                if user_messages:
                    summary["user_prompt_preview"] = _truncate(user_messages[-1], MAX_LOG_PREVIEW_CHARS)
            response_format = payload.get("response_format")
            if isinstance(response_format, dict):
                json_schema = response_format.get("json_schema")
                if isinstance(json_schema, dict):
                    summary["schema_name"] = json_schema.get("name")
                    schema = json_schema.get("schema")
                    if isinstance(schema, dict):
                        summary["schema_keys"] = sorted(schema)
            summary["inference_parameter_keys"] = sorted(
                key
                for key in payload
                if key not in {"model", "messages", "response_format"}
            )
        elif path == "/embeddings":
            raw_input = payload.get("input")
            if isinstance(raw_input, list):
                summary["input_count"] = len(raw_input)
                summary["input_chars"] = [
                    len(item)
                    for item in raw_input
                    if isinstance(item, str)
                ]
                if raw_input and isinstance(raw_input[0], str):
                    summary["first_input_preview"] = _truncate(raw_input[0], MAX_LOG_PREVIEW_CHARS)
        return summary

    @staticmethod
    def _summarize_response_payload(
        path: str,
        payload: dict[str, object],
        raw_response_chars: int,
    ) -> dict[str, Any]:
        """Вернуть безопасную сводку ответа LM Studio."""

        summary: dict[str, Any] = {
            "model": payload.get("model"),
            "response_keys": sorted(payload),
            "raw_response_chars": raw_response_chars,
        }
        if path == "/chat/completions":
            choices = payload.get("choices")
            if isinstance(choices, list):
                summary["choice_count"] = len(choices)
                if choices and isinstance(choices[0], dict):
                    message = choices[0].get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            summary["first_content_chars"] = len(content)
                            summary["first_content_preview"] = _truncate(content, MAX_LOG_PREVIEW_CHARS)
                        elif isinstance(content, dict):
                            summary["first_content_keys"] = sorted(content)
        elif path == "/embeddings":
            data = payload.get("data")
            if isinstance(data, list):
                summary["embedding_count"] = len(data)
                if data and isinstance(data[0], dict):
                    embedding = data[0].get("embedding")
                    if isinstance(embedding, list):
                        summary["embedding_dimension"] = len(embedding)
        return summary


def _read_http_error_body(error: HTTPError) -> str:
    """Прочитать тело HTTPError, не ломаясь на бинарном или отсутствующем payload."""

    try:
        raw_body = error.read()
    except Exception:
        return ""
    if not raw_body:
        return ""
    try:
        return raw_body.decode("utf-8", errors="replace")
    except AttributeError:
        return str(raw_body)


def _truncate(value: str, max_chars: int = MAX_LOG_PREVIEW_CHARS) -> str:
    """Обрезать длинные upstream/debug строки до безопасного размера."""

    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}...<truncated {len(value) - max_chars} chars>"
