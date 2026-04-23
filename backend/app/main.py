"""Backend bootstrap entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from backend.app.api.correlation import REQUEST_ID_HEADER
from backend.app.api.correlation import bind_correlation_id
from backend.app.api.correlation import install_correlation_log_record_factory
from backend.app.api.correlation import reset_correlation_id
from backend.app.api.documents import register_document_routes
from backend.app.api.errors import handle_backend_error
from backend.app.api.errors import handle_request_validation_error
from backend.app.api.generation import register_generation_routes
from backend.app.api.health import register_health_routes
from backend.app.api.quizzes import register_quiz_routes
from backend.app.api.runtime import resolve_default_storage_root
from backend.app.core.config import AppConfig
from backend.app.domain.errors import BackendError
from backend.app.llm.lm_studio import LMStudioClient

logger = logging.getLogger(__name__)


def create_app(
    config: AppConfig | None = None,
    provider=None,
    storage_root: Path | None = None,
) -> FastAPI:
    """Create the HTTP application for the backend."""

    resolved_config = config or AppConfig.from_env()
    install_correlation_log_record_factory()
    logging.basicConfig(
        level=getattr(logging, resolved_config.log_level, logging.INFO),
        format=resolved_config.log_format,
        force=True,
    )
    app = FastAPI(title="QuizCraft Backend")
    app.state.config = resolved_config
    app.state.storage_root = Path(storage_root) if storage_root is not None else resolve_default_storage_root()
    app.state.provider = provider or LMStudioClient(
        base_url=resolved_config.lm_studio_base_url,
        default_model=resolved_config.lm_studio_model,
        timeout_seconds=resolved_config.request_timeout,
    )
    app.add_exception_handler(BackendError, handle_backend_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    register_health_routes(app, resolved_config)
    register_document_routes(app)
    register_generation_routes(app)
    register_quiz_routes(app)

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        token = bind_correlation_id(request_id)
        request.state.correlation_id = request_id
        logger.info("HTTP request started method=%s path=%s", request.method, request.url.path)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "HTTP request completed method=%s path=%s status=%s",
                request.method,
                request.url.path,
                response.status_code,
            )
            return response
        finally:
            reset_correlation_id(token)

    return app
