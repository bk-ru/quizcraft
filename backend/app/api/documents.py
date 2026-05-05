"""Endpoint загрузки документов для HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.api.runtime import get_document_ingestion_service
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
        content = await request.body()
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
