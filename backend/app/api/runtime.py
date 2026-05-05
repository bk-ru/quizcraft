"""Ленивая runtime-сборка для API endpoint'ов, которым нужны backend-сервисы."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from backend.app.core.config import AppConfig
from backend.app.generation import DirectGenerationOrchestrator
from backend.app.generation import DirectGenerationRequestBuilder
from backend.app.generation import FileSystemGenerationDiagnosticLogger
from backend.app.generation import GenerationOrchestratorDispatcher
from backend.app.generation import GenerationQualityChecker
from backend.app.generation import RagGenerationOrchestrator
from backend.app.generation import SingleQuestionRegenerationOrchestrator
from backend.app.generation import SingleQuestionRegenerationRequestBuilder
from backend.app.parsing.docx import DocxParser
from backend.app.parsing.files import UploadedFileValidator
from backend.app.parsing.ingestion import DocumentIngestionService
from backend.app.parsing.pdf import PdfParser
from backend.app.parsing.txt import TxtParser
from backend.app.prompts.registry import PromptRegistry
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.generation_settings import FileSystemGenerationSettingsRepository
from backend.app.storage.quizzes import FileSystemQuizRepository
from backend.app.storage.rag_cache import FileSystemRagCacheRepository

DEFAULT_STORAGE_DIRECTORY_NAME = ".quizcraft"


def resolve_default_storage_root() -> Path:
    """Определить корень файловой системы по умолчанию для сохраняемых backend-артефактов."""

    return Path.cwd() / DEFAULT_STORAGE_DIRECTORY_NAME


def get_document_ingestion_service(app: FastAPI) -> DocumentIngestionService:
    """Получить или лениво создать сервис ingestion документов для приложения FastAPI."""

    service = getattr(app.state, "document_ingestion_service", None)
    if service is None:
        service = _build_document_ingestion_service(
            config=app.state.config,
            storage_root=app.state.storage_root,
        )
        app.state.document_ingestion_service = service
    return service


def get_generation_orchestrator(app: FastAPI) -> DirectGenerationOrchestrator:
    """Получить или лениво создать orchestrator прямой генерации для приложения FastAPI."""

    orchestrator = getattr(app.state, "generation_orchestrator", None)
    if orchestrator is None:
        orchestrator = DirectGenerationOrchestrator(
            document_repository=_get_document_repository(app.state.storage_root),
            quiz_repository=FileSystemQuizRepository(app.state.storage_root),
            generation_result_repository=FileSystemGenerationResultRepository(app.state.storage_root),
            request_builder=DirectGenerationRequestBuilder(prompt_registry=PromptRegistry),
            provider=app.state.provider,
            quality_checker=GenerationQualityChecker(),
            max_document_chars=app.state.config.max_document_chars,
            diagnostic_logger=get_generation_diagnostic_logger(app),
        )
        app.state.generation_orchestrator = orchestrator
    return orchestrator


def get_rag_generation_orchestrator(app: FastAPI) -> RagGenerationOrchestrator:
    """Получить или лениво создать orchestrator RAG-генерации для приложения FastAPI."""

    orchestrator = getattr(app.state, "rag_generation_orchestrator", None)
    if orchestrator is None:
        orchestrator = RagGenerationOrchestrator(
            document_repository=_get_document_repository(app.state.storage_root),
            quiz_repository=FileSystemQuizRepository(app.state.storage_root),
            generation_result_repository=FileSystemGenerationResultRepository(app.state.storage_root),
            provider=app.state.provider,
            quality_checker=GenerationQualityChecker(),
            max_document_chars=app.state.config.max_document_chars,
            embedding_model_name=app.state.config.default_embedding_model,
            rag_cache_repository=FileSystemRagCacheRepository(app.state.storage_root),
            diagnostic_logger=get_generation_diagnostic_logger(app),
        )
        app.state.rag_generation_orchestrator = orchestrator
    return orchestrator


def get_generation_dispatcher(app: FastAPI) -> GenerationOrchestratorDispatcher:
    """Получить или лениво создать dispatcher генерации, маршрутизирующий direct и rag пути."""

    dispatcher = getattr(app.state, "generation_dispatcher", None)
    if dispatcher is None:
        dispatcher = GenerationOrchestratorDispatcher(
            direct_orchestrator=get_generation_orchestrator(app),
            rag_orchestrator=get_rag_generation_orchestrator(app),
            document_repository=_get_document_repository(app.state.storage_root),
        )
        app.state.generation_dispatcher = dispatcher
    return dispatcher


def get_generation_settings_repository(app: FastAPI) -> FileSystemGenerationSettingsRepository:
    """Получить или лениво создать repository настроек генерации для приложения FastAPI."""

    repository = getattr(app.state, "generation_settings_repository", None)
    if repository is None:
        repository = FileSystemGenerationSettingsRepository(app.state.storage_root)
        app.state.generation_settings_repository = repository
    return repository


def get_generation_diagnostic_logger(app: FastAPI) -> FileSystemGenerationDiagnosticLogger:
    """Получить или лениво создать filesystem logger диагностических артефактов генерации."""

    diagnostic_logger = getattr(app.state, "generation_diagnostic_logger", None)
    if diagnostic_logger is None:
        diagnostic_logger = FileSystemGenerationDiagnosticLogger(app.state.storage_root)
        app.state.generation_diagnostic_logger = diagnostic_logger
    return diagnostic_logger


def get_single_question_regeneration_orchestrator(app: FastAPI) -> SingleQuestionRegenerationOrchestrator:
    """Получить или лениво создать orchestrator точечной регенерации вопросов."""

    orchestrator = getattr(app.state, "single_question_regeneration_orchestrator", None)
    if orchestrator is None:
        orchestrator = SingleQuestionRegenerationOrchestrator(
            document_repository=_get_document_repository(app.state.storage_root),
            quiz_repository=FileSystemQuizRepository(app.state.storage_root),
            request_builder=SingleQuestionRegenerationRequestBuilder(prompt_registry=PromptRegistry),
            provider=app.state.provider,
        )
        app.state.single_question_regeneration_orchestrator = orchestrator
    return orchestrator


def _build_document_ingestion_service(
    config: AppConfig,
    storage_root: Path,
) -> DocumentIngestionService:
    """Сформировать конкретный граф сервисов для ingestion документов."""

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
    """Сформировать общий repository документов для потоков загрузки и генерации."""

    return FileSystemDocumentRepository(storage_root)
