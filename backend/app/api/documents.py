"""Endpoint загрузки документов для HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.api.runtime import get_document_ingestion_service
from backend.app.domain.errors import DocumentTooLargeError
from backend.app.domain.errors import FileValidationError
from backend.app.domain.models import DocumentRecord

UPLOAD_FILENAME_HEADER = "X-Filename"


def register_document_routes(app: FastAPI) -> None:
    """Зарегистрировать маршруты загрузки документов в приложении FastAPI."""

    @app.post("/documents")
    async def upload_document(request: Request) -> JSONResponse:
        filename = (
            request.query_params.get("filename", "").strip()
            or request.headers.get(UPLOAD_FILENAME_HEADER, "").strip()
        )
        media_type = request.headers.get("Content-Type", "").strip()
        content = await _read_limited_body(
            request,
            max_size_bytes=request.app.state.config.max_file_size_mb * 1024 * 1024,
        )
        if not filename:
            raise FileValidationError("filename is required")

        document = get_document_ingestion_service(request.app).ingest(
            filename=filename,
            media_type=media_type,
            content=content,
        )
        return JSONResponse(
            status_code=201,
            content=_serialize_document(document, request.state.correlation_id),
        )


async def _read_limited_body(request: Request, *, max_size_bytes: int) -> bytes:
    """Read an upload body without allowing it to exceed the configured byte limit."""

    content_length = _parse_content_length(request)
    if content_length is not None and content_length > max_size_bytes:
        raise DocumentTooLargeError(
            f"uploaded file size exceeds limit: {content_length} bytes > {max_size_bytes} bytes"
        )

    chunks: list[bytes] = []
    total_size = 0
    async for chunk in request.stream():
        if not chunk:
            continue
        total_size += len(chunk)
        if total_size > max_size_bytes:
            raise DocumentTooLargeError(
                f"uploaded file size exceeds limit: {total_size} bytes > {max_size_bytes} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_content_length(request: Request) -> int | None:
    raw_content_length = request.headers.get("Content-Length")
    if raw_content_length is None:
        return None
    try:
        content_length = int(raw_content_length)
    except ValueError as error:
        raise FileValidationError("Content-Length must be an integer") from error
    if content_length < 0:
        raise FileValidationError("Content-Length must not be negative")
    return content_length


def _serialize_document(document: DocumentRecord, request_id: str) -> dict[str, Any]:
    """Сериализовать сохраненную запись документа для API-ответов."""

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "media_type": document.media_type,
        "file_size_bytes": document.file_size_bytes,
        "metadata": document.metadata,
        "request_id": request_id,
    }
