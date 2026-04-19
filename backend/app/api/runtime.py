"""Lazy runtime wiring for API endpoints that need backend services."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from backend.app.core.config import AppConfig
from backend.app.generation import DirectGenerationOrchestrator
from backend.app.generation import DirectGenerationRequestBuilder
from backend.app.generation import GenerationQualityChecker
from backend.app.parsing.docx import DocxParser
from backend.app.parsing.files import UploadedFileValidator
from backend.app.parsing.ingestion import DocumentIngestionService
from backend.app.parsing.pdf import PdfParser
from backend.app.parsing.txt import TxtParser
from backend.app.prompts.registry import PromptRegistry
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository

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


def get_generation_orchestrator(app: FastAPI) -> DirectGenerationOrchestrator:
    """Get or lazily build the direct-generation orchestrator for the FastAPI app."""

    orchestrator = getattr(app.state, "generation_orchestrator", None)
    if orchestrator is None:
        document_repository = _get_document_repository(app.state.storage_root)
        quiz_repository = FileSystemQuizRepository(app.state.storage_root)
        generation_result_repository = FileSystemGenerationResultRepository(app.state.storage_root)
        orchestrator = DirectGenerationOrchestrator(
            document_repository=document_repository,
            quiz_repository=quiz_repository,
            generation_result_repository=generation_result_repository,
            request_builder=DirectGenerationRequestBuilder(prompt_registry=PromptRegistry),
            provider=app.state.provider,
            quality_checker=GenerationQualityChecker(),
        )
        app.state.generation_orchestrator = orchestrator
    return orchestrator


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


def _get_document_repository(storage_root: Path) -> FileSystemDocumentRepository:
    """Build the shared document repository for upload and generation flows."""

    return FileSystemDocumentRepository(storage_root)
