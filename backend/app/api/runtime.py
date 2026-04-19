"""Lazy runtime wiring for API endpoints that need upload services."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from backend.app.core.config import AppConfig
from backend.app.parsing.docx import DocxParser
from backend.app.parsing.files import UploadedFileValidator
from backend.app.parsing.ingestion import DocumentIngestionService
from backend.app.parsing.pdf import PdfParser
from backend.app.parsing.txt import TxtParser
from backend.app.storage.documents import FileSystemDocumentRepository

DEFAULT_STORAGE_DIRECTORY_NAME = ".quizcraft"


def resolve_default_storage_root() -> Path:
    """Resolve the default filesystem root for persisted backend artifacts."""

    return Path.cwd() / DEFAULT_STORAGE_DIRECTORY_NAME


def get_document_ingestion_service(app: FastAPI) -> DocumentIngestionService:
    """Get or lazily build the document-ingestion service for the FastAPI app."""

    service = getattr(app.state, "document_ingestion_service", None)
    if service is None:
        service = _build_document_ingestion_service(
            config=app.state.config,
            storage_root=app.state.storage_root,
        )
        app.state.document_ingestion_service = service
    return service


def _build_document_ingestion_service(
    config: AppConfig,
    storage_root: Path,
) -> DocumentIngestionService:
    """Build the concrete service graph for document ingestion."""

    document_repository = FileSystemDocumentRepository(storage_root)
    validator = UploadedFileValidator(max_file_size_bytes=config.max_file_size_mb * 1024 * 1024)
    return DocumentIngestionService(
        repository=document_repository,
        validator=validator,
        txt_parser=TxtParser(),
        docx_parser=DocxParser(),
        pdf_parser=PdfParser(),
    )
