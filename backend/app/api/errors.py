"""HTTP error mapping for controlled backend exceptions."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.correlation import get_correlation_id
from backend.app.api.schemas import build_validation_error_message
from backend.app.domain.errors import BackendError
from backend.app.domain.errors import ConfigurationError
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import FileValidationError
from backend.app.domain.errors import LLMConnectionError
from backend.app.domain.errors import LLMRequestError
from backend.app.domain.errors import LLMResponseFormatError
from backend.app.domain.errors import LLMServerError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.domain.errors import PromptResolutionError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.errors import TextExtractionError
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.errors import UnsupportedProviderCapabilityError

logger = logging.getLogger(__name__)


def map_backend_error_to_status_code(error: BackendError) -> int:
    """Map one domain error into a stable HTTP status code."""

    if isinstance(error, RepositoryNotFoundError):
        return 404
    if isinstance(error, (FileValidationError, TextExtractionError, UnsupportedGenerationModeError)):
        return 400
    if isinstance(error, DomainValidationError):
        return 422
    if isinstance(error, LLMTimeoutError):
        return 504
    if isinstance(error, LLMConnectionError):
        return 503
    if isinstance(error, (LLMRequestError, LLMServerError, LLMResponseFormatError)):
        return 502
    if isinstance(error, UnsupportedProviderCapabilityError):
        return 501
    if isinstance(error, (ConfigurationError, PromptResolutionError)):
        return 500
    return 500


async def handle_backend_error(request: Request, error: BackendError) -> JSONResponse:
    """Convert a controlled backend exception into a JSON HTTP response."""

    request_id = getattr(request.state, "correlation_id", get_correlation_id())
    logger.warning("HTTP backend error code=%s status=%s", error.code, map_backend_error_to_status_code(error))
    return JSONResponse(
        status_code=map_backend_error_to_status_code(error),
        content={
            "error": {
                "code": error.code,
                "message": error.message,
            },
            "request_id": request_id,
        },
    )


async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """Render FastAPI request-validation errors using the backend error envelope."""

    request_id = getattr(request.state, "correlation_id", get_correlation_id())
    message = build_validation_error_message(list(error.errors()))
    logger.warning("HTTP request validation error message=%s", message)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": message,
            },
            "request_id": request_id,
        },
    )
