"""Orchestrator retrieval-augmented generation с ограниченной поддержкой repair."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import replace
from typing import Any
from typing import Callable
from typing import TypeVar
from uuid import uuid4

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DocumentTooLargeForGenerationError
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.domain.normalization import normalize_quiz_output
from backend.app.domain.normalization import resolve_readable_quiz_title
from backend.app.generation.context import assemble_context
from backend.app.generation.diagnostics import FileSystemGenerationDiagnosticLogger
from backend.app.generation.diagnostics import summarize_structured_generation_request
from backend.app.generation.matching_fallback import build_matching_pair_count_error
from backend.app.generation.matching_fallback import fallback_invalid_matching_questions
from backend.app.generation.matching_fallback import is_matching_pair_count_error
from backend.app.generation.matching_fallback import prepare_repair_source_text
from backend.app.generation.pipeline_logging import log_generation_pipeline_event
from backend.app.generation.quality import GenerationQualityChecker
from backend.app.generation.quality import enrich_generation_error
from backend.app.generation.quality import fit_generated_question_count
from backend.app.generation.question_types import render_question_type_policy
from backend.app.generation.question_types import render_question_type_rules
from backend.app.generation.rag_cache import RagCacheEntry
from backend.app.generation.rag_cache import build_document_hash
from backend.app.generation.rag_cache import build_rag_cache_key
from backend.app.generation.retrieval import InMemoryVectorIndex
from backend.app.generation.retrieval import EmbeddedChunk
from backend.app.generation.retrieval import embed_chunks
from backend.app.generation.safe_logging import summarize_document_payload
from backend.app.generation.safe_logging import summarize_generation_request
from backend.app.generation.safe_logging import summarize_generation_result
from backend.app.generation.safe_logging import summarize_model_payload
from backend.app.generation.status import GenerationPipelineEvent
from backend.app.generation.status import GenerationPipelineStep
from backend.app.generation.status import GenerationRunStatus
from backend.app.parsing.chunking import chunk_text
from backend.app.parsing.chunking import TextChunk
from backend.app.prompts.registry import PromptRegistry
from backend.app.prompts.registry import RAG_GENERATION_PROMPT_KEY
from backend.app.prompts.registry import REPAIR_GENERATION_PROMPT_KEY

logger = logging.getLogger(__name__)
PipelineResult = TypeVar("PipelineResult")

DEFAULT_RAG_CHUNK_SIZE = 800
DEFAULT_RAG_CHUNK_OVERLAP = 120
DEFAULT_RAG_TOP_K = 8
DEFAULT_RAG_MAX_CONTEXT_CHARS = 4000
DEFAULT_RAG_CACHE_EMBEDDING_MODEL_NAME = "__provider_default__"


def build_default_rag_query(generation_request: GenerationRequest) -> str:
    """Сформировать детерминированную строку retrieval-запроса из запроса генерации."""

    return (
        "Создай {count} вопросов на языке {language}, "
        "сложность {difficulty}, тип {quiz_type}, "
        "опираясь только на содержание документа."
    ).format(
        count=generation_request.question_count,
        language=generation_request.language,
        difficulty=generation_request.difficulty,
        quiz_type=generation_request.quiz_type,
    )


class RagGenerationOrchestrator:
    """Генерировать квизы через retrieval-augmented prompts с ограниченной поддержкой repair."""

    def __init__(
        self,
        document_repository,
        quiz_repository,
        generation_result_repository,
        provider,
        quality_checker: GenerationQualityChecker,
        normalizer: Callable[[dict[str, Any]], Quiz] = normalize_quiz_output,
        prompt_registry: type[PromptRegistry] = PromptRegistry,
        max_repair_attempts: int = 1,
        max_document_chars: int | None = None,
        chunk_size: int = DEFAULT_RAG_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_RAG_CHUNK_OVERLAP,
        top_k: int = DEFAULT_RAG_TOP_K,
        max_context_chars: int = DEFAULT_RAG_MAX_CONTEXT_CHARS,
        embedding_model_name: str | None = None,
        query_builder: Callable[[GenerationRequest], str] = build_default_rag_query,
        rag_cache_repository=None,
        diagnostic_logger: FileSystemGenerationDiagnosticLogger | None = None,
    ) -> None:
        self._validate_construction_inputs(
            max_document_chars=max_document_chars,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=top_k,
            max_context_chars=max_context_chars,
        )
        self._document_repository = document_repository
        self._quiz_repository = quiz_repository
        self._generation_result_repository = generation_result_repository
        self._provider = provider
        self._quality_checker = quality_checker
        self._normalizer = normalizer
        self._prompt_registry = prompt_registry
        self._max_repair_attempts = max_repair_attempts
        self._max_document_chars = max_document_chars
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._top_k = top_k
        self._max_context_chars = max_context_chars
        self._embedding_model_name = embedding_model_name
        self._query_builder = query_builder
        self._rag_cache_repository = rag_cache_repository
        self._diagnostic_logger = diagnostic_logger

    def generate(self, document_id: str, generation_request: GenerationRequest) -> GenerationResult:
        """Выполнить полный RAG pipeline для одного документа и сохранить итоговый квиз."""
        start_time = time.perf_counter()
        pipeline_mode = "rag"

        if generation_request.generation_mode is not GenerationMode.RAG:
            raise UnsupportedGenerationModeError(
                f"unsupported generation mode for rag orchestrator: {generation_request.generation_mode}"
            )

        self._log_pipeline_step(
            status=GenerationRunStatus.QUEUED,
            step=GenerationPipelineStep.PARSE,
            document_id=document_id,
            generation_request=generation_request,
        )
        document = self._run_pipeline_step(
            step=GenerationPipelineStep.PARSE,
            document_id=document_id,
            generation_request=generation_request,
            operation=lambda: self._load_generation_document(document_id),
            metadata_builder=summarize_document_payload,
        )

        try:
            (
                rag_response,
                rag_prompt_version,
                _,
                _,
                provider_request_summary,
                rag_metadata,
                repair_source_text,
            ) = self._run_pipeline_step(
                step=GenerationPipelineStep.GENERATE,
                document_id=document.document_id,
                generation_request=generation_request,
                operation=lambda: self._request_rag_generation(document, generation_request),
                metadata_builder=lambda result: {
                    "model_name": result[0].model_name,
                    "model_payload": summarize_model_payload(result[0].content),
                    "context_chars": result[2],
                    "retrieved_chunks": result[3],
                },
            )
        except Exception as error:
            self._log_diagnostic_runtime_failure(
                document=document,
                generation_request=generation_request,
                stage=GenerationPipelineStep.GENERATE.value,
                error=error,
            )
            raise

        quiz, final_response, prompt_version, final_provider_request_summary = self._finalize_generation(
            document=document,
            generation_request=generation_request,
            response=rag_response,
            rag_prompt_version=rag_prompt_version,
            provider_request_summary=provider_request_summary,
            rag_metadata=rag_metadata,
            repair_source_text=repair_source_text,
        )
        self._log_diagnostic_success(
            document=document,
            generation_request=generation_request,
            response=final_response,
            prompt_version=prompt_version,
            provider_request_summary=final_provider_request_summary,
            quiz=quiz,
            rag_metadata=rag_metadata,
        )
        try:
            result = self._run_pipeline_step(
                step=GenerationPipelineStep.PERSIST,
                document_id=document.document_id,
                generation_request=generation_request,
                operation=lambda: self._persist_generation_result(
                    quiz,
                    generation_request,
                    final_response,
                    prompt_version,
                ),
                quiz_id=quiz.quiz_id,
                metadata_builder=summarize_generation_result,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "Generation timing document_chars=%d mode=%s model=%s elapsed_ms=%d",
                len(document.normalized_text),
                pipeline_mode,
                final_response.model_name,
                elapsed_ms,
            )
            return result
        except Exception as error:
            self._log_diagnostic_runtime_failure(
                document=document,
                generation_request=generation_request,
                stage=GenerationPipelineStep.PERSIST.value,
                error=error,
                rag_metadata=rag_metadata,
            )
            raise

    def _load_generation_document(self, document_id: str) -> DocumentRecord:
        """Загрузить и защитно проверить сохраненный документ перед генерацией."""

        document = self._document_repository.get(document_id)
        self._guard_document_length(document)
        logger.info(
            "Starting rag generation document=%s",
            summarize_document_payload(document),
        )
        return document

    def _request_rag_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
    ) -> tuple[StructuredGenerationResponse, str, int, int, dict[str, Any], dict[str, Any]]:
        """Выполнить chunk -> embed -> retrieve -> assemble -> generate и вернуть метрики контекста."""

        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "rag_chunking"},
        )
        chunks = chunk_text(
            document.normalized_text,
            chunk_size=self._chunk_size,
            overlap=self._chunk_overlap,
        )
        if not chunks:
            raise DomainValidationError(
                f"document '{document.document_id}' has no content for retrieval"
            )

        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "rag_embedding", "chunk_count": len(chunks)},
        )
        embedded = self._load_or_embed_chunks(
            document=document,
            chunks=chunks,
        )
        index = InMemoryVectorIndex(embedded)

        query_text = self._query_builder(generation_request)
        query_response = self._provider.embed(
            EmbeddingRequest(
                texts=(query_text,),
                model_name=self._embedding_model_name,
            )
        )
        if not query_response.vectors:
            raise DomainValidationError("embedding provider returned no query vector")
        query_vector = query_response.vectors[0]

        scored = index.search(query_vector, top_k=self._top_k)
        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "rag_retrieval", "retrieved_chunks": len(scored)},
        )
        context = assemble_context(scored, max_chars=self._max_context_chars)
        if not context:
            raise DomainValidationError(
                f"retrieved context is empty for document '{document.document_id}'"
            )

        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "rag_context", "context_chars": len(context)},
        )
        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "rag_request"},
        )
        rag_prompt = self._prompt_registry.resolve(RAG_GENERATION_PROMPT_KEY)
        provider_request = StructuredGenerationRequest(
            system_prompt=rag_prompt.system_template,
            user_prompt=rag_prompt.user_template.format(
                document_id=document.document_id,
                retrieved_context=context,
                question_count=generation_request.question_count,
                language=generation_request.language,
                difficulty=generation_request.difficulty,
                quiz_type=generation_request.quiz_type,
                question_type_policy=render_question_type_policy(generation_request),
                question_type_rules=render_question_type_rules(generation_request),
            ),
            schema_name=rag_prompt.schema_name,
            schema=rag_prompt.schema,
            inference_parameters={
                **rag_prompt.inference_parameters,
                **generation_request.inference_parameters,
            },
            model_name=generation_request.model_name,
        )
        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "awaiting_provider"},
        )
        response = self._provider.generate_structured(provider_request)
        rag_metadata = {
            "chunk_count": len(chunks),
            "embedding_model_name": self._cache_embedding_model_name(),
            "query_chars": len(query_text),
            "retrieved_chunks": len(scored),
            "context_chars": len(context),
            "top_k": self._top_k,
            "max_context_chars": self._max_context_chars,
        }
        return (
            response,
            rag_prompt.version,
            len(context),
            len(scored),
            summarize_structured_generation_request(provider_request),
            rag_metadata,
            context,
        )

    def _load_or_embed_chunks(
        self,
        *,
        document: DocumentRecord,
        chunks: tuple[TextChunk, ...],
    ) -> tuple[EmbeddedChunk, ...]:
        """Загрузить кэшированные chunk embeddings при наличии, иначе создать embeddings и сохранить их."""

        if self._rag_cache_repository is None:
            return embed_chunks(
                chunks,
                provider=self._provider,
                model_name=self._embedding_model_name,
            )

        document_hash = build_document_hash(document.normalized_text)
        embedding_model_name = self._cache_embedding_model_name()
        cache_key = build_rag_cache_key(
            document_hash=document_hash,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            embedding_model_name=embedding_model_name,
        )
        try:
            cache_entry = self._rag_cache_repository.get(cache_key)
        except RepositoryNotFoundError:
            embedded = embed_chunks(
                chunks,
                provider=self._provider,
                model_name=self._embedding_model_name,
            )
            self._rag_cache_repository.save(
                RagCacheEntry(
                    document_hash=document_hash,
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                    embedding_model_name=embedding_model_name,
                    embedded_chunks=embedded,
                )
            )
            logger.info("Stored rag cache entry document_hash=%s cache_key=%s", document_hash, cache_key)
            return embedded

        logger.info("Loaded rag cache entry document_hash=%s cache_key=%s", document_hash, cache_key)
        return cache_entry.embedded_chunks

    def _cache_embedding_model_name(self) -> str:
        """Вернуть видимый для кэша идентификатор embedding-модели."""

        return self._embedding_model_name or DEFAULT_RAG_CACHE_EMBEDDING_MODEL_NAME

    def _finalize_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        rag_prompt_version: str,
        provider_request_summary: dict[str, Any],
        rag_metadata: dict[str, Any],
        repair_source_text: str,
    ) -> tuple[Quiz, StructuredGenerationResponse, str, dict[str, Any]]:
        """Нормализовать и проверить RAG-ответ, затем при необходимости попробовать repair."""

        try:
            quiz = self._normalize_and_validate(
                document,
                generation_request,
                response,
                prompt_version=rag_prompt_version,
                provider_request_summary=provider_request_summary,
                rag_metadata=rag_metadata,
            )
        except DomainValidationError as error:
            return self._repair_generation(
                document,
                generation_request,
                response,
                initial_error=error,
                initial_prompt_version=rag_prompt_version,
                initial_provider_request_summary=provider_request_summary,
                rag_metadata=rag_metadata,
                repair_source_text=repair_source_text,
            )
        return quiz, response, rag_prompt_version, provider_request_summary

    def _normalize_and_validate(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        *,
        prompt_version: str,
        provider_request_summary: dict[str, Any],
        rag_metadata: dict[str, Any],
        repair_attempt: int | None = None,
    ) -> Quiz:
        """Нормализовать и проверить структурированный RAG-ответ."""

        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "validation"},
        )
        logger.info(
            "Received provider response model=%s payload=%s",
            response.model_name,
            summarize_model_payload(response.content),
        )
        try:
            quiz = replace(
                self._normalizer(response.content),
                quiz_id=f"quiz-{uuid4().hex}",
                document_id=document.document_id,
            )
        except DomainValidationError as error:
            self._log_diagnostic_validation_failure(
                document=document,
                generation_request=generation_request,
                response=response,
                prompt_version=prompt_version,
                provider_request_summary=provider_request_summary,
                error=error,
                rag_metadata=rag_metadata,
                repair_attempt=repair_attempt,
            )
            raise
        quiz = fit_generated_question_count(quiz, generation_request.question_count)
        readable_title = resolve_readable_quiz_title(
            quiz.title,
            document.filename,
            len(quiz.questions),
        )
        quiz = replace(quiz, title=readable_title)
        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            metadata={"phase": "quality_check"},
        )
        try:
            self._quality_checker.ensure_quality(quiz, generation_request.question_count)
        except DomainValidationError as error:
            self._log_diagnostic_validation_failure(
                document=document,
                generation_request=generation_request,
                response=response,
                prompt_version=prompt_version,
                provider_request_summary=provider_request_summary,
                error=error,
                quiz=quiz,
                rag_metadata=rag_metadata,
                repair_attempt=repair_attempt,
            )
            raise
        return quiz

    def _repair_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        initial_error: DomainValidationError,
        initial_prompt_version: str,
        initial_provider_request_summary: dict[str, Any],
        rag_metadata: dict[str, Any],
        repair_source_text: str,
    ) -> tuple[Quiz, StructuredGenerationResponse, str, dict[str, Any]]:
        """Попробовать ограниченный repair-проход для некорректного нормализованного вывода."""

        repair_prompt = self._prompt_registry.resolve(REPAIR_GENERATION_PROMPT_KEY)
        current_error: DomainValidationError = initial_error
        current_response = response
        current_prompt_version = initial_prompt_version
        current_provider_request_summary = initial_provider_request_summary

        for attempt_index in range(1, self._max_repair_attempts + 1):
            logger.warning(
                "Rag repair attempt=%s validation_error=%s payload=%s",
                attempt_index,
                current_error.message,
                summarize_model_payload(current_response.content),
            )
            self._log_pipeline_step(
                status=GenerationRunStatus.RUNNING,
                step=GenerationPipelineStep.REPAIR,
                document_id=document.document_id,
                generation_request=generation_request,
                metadata={
                    "attempt": attempt_index,
                    "initial_error_code": current_error.code,
                    "model_payload": summarize_model_payload(current_response.content),
                },
            )
            try:
                repair_request = self._build_repair_request(
                    repair_prompt,
                    current_response,
                    current_error,
                    generation_request,
                    source_text=repair_source_text,
                )
                current_provider_request_summary = summarize_structured_generation_request(repair_request)
                current_response = self._provider.generate_structured(repair_request)
                current_prompt_version = repair_prompt.version
                repaired_quiz = self._normalize_and_validate(
                    document=document,
                    generation_request=generation_request,
                    response=current_response,
                    prompt_version=current_prompt_version,
                    provider_request_summary=current_provider_request_summary,
                    rag_metadata=rag_metadata,
                    repair_attempt=attempt_index,
                )
            except DomainValidationError as error:
                current_error = error
                self._log_pipeline_step(
                    status=GenerationRunStatus.FAILED,
                    step=GenerationPipelineStep.REPAIR,
                    document_id=document.document_id,
                    generation_request=generation_request,
                    metadata={"attempt": attempt_index},
                    error=error,
                )
                continue
            except Exception as error:
                self._log_pipeline_step(
                    status=GenerationRunStatus.FAILED,
                    step=GenerationPipelineStep.REPAIR,
                    document_id=document.document_id,
                    generation_request=generation_request,
                    metadata={"attempt": attempt_index},
                    error=error,
                )
                raise
            self._log_pipeline_step(
                status=GenerationRunStatus.DONE,
                step=GenerationPipelineStep.REPAIR,
                document_id=document.document_id,
                generation_request=generation_request,
                quiz_id=repaired_quiz.quiz_id,
                metadata={
                    "attempt": attempt_index,
                    "model_name": current_response.model_name,
                    "model_payload": summarize_model_payload(current_response.content),
                },
            )
            return repaired_quiz, current_response, repair_prompt.version, current_provider_request_summary

        fallback_result = self._try_matching_fallback(
            document=document,
            generation_request=generation_request,
            response=current_response,
            prompt_version=current_prompt_version,
            provider_request_summary=current_provider_request_summary,
        )
        if fallback_result is not None:
            return fallback_result

        if is_matching_pair_count_error(current_error) and isinstance(current_response.content, dict):
            raise build_matching_pair_count_error(current_response.content)
        raise enrich_generation_error(
            current_error,
            len(document.normalized_text),
            requested_question_count=generation_request.question_count,
        )

    def _try_matching_fallback(
        self,
        *,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        prompt_version: str,
        provider_request_summary: dict[str, Any],
    ) -> tuple[Quiz, StructuredGenerationResponse, str, dict[str, Any]] | None:
        if not isinstance(response.content, dict):
            return None
        try:
            quiz = replace(
                self._normalizer(response.content),
                quiz_id=f"quiz-{uuid4().hex}",
                document_id=document.document_id,
            )
        except DomainValidationError:
            return None
        fallback_quiz = fallback_invalid_matching_questions(quiz, generation_request)
        if fallback_quiz is None:
            return None
        fallback_quiz = fit_generated_question_count(fallback_quiz, generation_request.question_count)
        fallback_quiz = replace(
            fallback_quiz,
            title=resolve_readable_quiz_title(
                fallback_quiz.title,
                document.filename,
                len(fallback_quiz.questions),
            ),
        )
        self._quality_checker.ensure_quality(fallback_quiz, generation_request.question_count)
        return fallback_quiz, response, prompt_version, provider_request_summary

    def _log_diagnostic_success(
        self,
        *,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        prompt_version: str,
        provider_request_summary: dict[str, Any],
        quiz: Quiz,
        rag_metadata: dict[str, Any],
    ) -> None:
        if self._diagnostic_logger is None:
            return
        self._diagnostic_logger.log_success(
            pipeline="rag",
            document=document,
            generation_request=generation_request,
            prompt_version=prompt_version,
            provider_request=provider_request_summary,
            response=response,
            quiz=quiz,
            rag_metadata=rag_metadata,
        )

    def _log_diagnostic_validation_failure(
        self,
        *,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        prompt_version: str,
        provider_request_summary: dict[str, Any],
        error: DomainValidationError,
        rag_metadata: dict[str, Any],
        quiz: Quiz | None = None,
        repair_attempt: int | None = None,
    ) -> None:
        if self._diagnostic_logger is None:
            return
        self._diagnostic_logger.log_validation_failure(
            pipeline="rag",
            document=document,
            generation_request=generation_request,
            prompt_version=prompt_version,
            provider_request=provider_request_summary,
            response=response,
            error=error,
            quiz=quiz,
            rag_metadata=rag_metadata,
            repair_attempt=repair_attempt,
        )

    def _log_diagnostic_runtime_failure(
        self,
        *,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        stage: str,
        error: Exception,
        rag_metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._diagnostic_logger is None:
            return
        self._diagnostic_logger.log_runtime_failure(
            pipeline="rag",
            document=document,
            generation_request=generation_request,
            stage=stage,
            error=error,
            rag_metadata=rag_metadata,
        )

    def _persist_generation_result(
        self,
        quiz: Quiz,
        generation_request: GenerationRequest,
        final_response: StructuredGenerationResponse,
        prompt_version: str,
    ) -> GenerationResult:
        """Сохранить сгенерированный квиз и метаданные его генерации."""

        persisted_quiz = self._quiz_repository.save(quiz)
        result = GenerationResult(
            quiz=persisted_quiz,
            request=generation_request,
            model_name=final_response.model_name,
            prompt_version=prompt_version,
        )
        self._generation_result_repository.save(result)
        logger.info("Persisted rag generation result summary=%s", summarize_generation_result(result))
        return result

    def _guard_document_length(self, document: DocumentRecord) -> None:
        """Отклонить документы, нормализованный текст которых превышает настроенный лимит."""

        if self._max_document_chars is None:
            return
        document_length = len(document.normalized_text)
        if document_length > self._max_document_chars:
            raise DocumentTooLargeForGenerationError(
                f"document '{document.document_id}' is too large for generation: "
                f"{document_length} characters exceeds limit of {self._max_document_chars}"
            )

    def _run_pipeline_step(
        self,
        *,
        step: GenerationPipelineStep,
        document_id: str,
        generation_request: GenerationRequest,
        operation: Callable[[], PipelineResult],
        quiz_id: str | None = None,
        metadata_builder: Callable[[PipelineResult], dict[str, Any]] | None = None,
    ) -> PipelineResult:
        """Выполнить один шаг rag pipeline и выпустить структурированные переходы статуса."""

        self._log_pipeline_step(
            status=GenerationRunStatus.RUNNING,
            step=step,
            document_id=document_id,
            generation_request=generation_request,
            quiz_id=quiz_id,
        )
        try:
            result = operation()
        except Exception as error:
            self._log_pipeline_step(
                status=GenerationRunStatus.FAILED,
                step=step,
                document_id=document_id,
                generation_request=generation_request,
                quiz_id=quiz_id,
                error=error,
            )
            raise

        self._log_pipeline_step(
            status=GenerationRunStatus.DONE,
            step=step,
            document_id=document_id,
            generation_request=generation_request,
            quiz_id=quiz_id,
            metadata={} if metadata_builder is None else metadata_builder(result),
        )
        return result

    @staticmethod
    def _log_pipeline_step(
        *,
        status: GenerationRunStatus,
        step: GenerationPipelineStep,
        document_id: str,
        generation_request: GenerationRequest,
        quiz_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        """Выпустить одно структурированное событие шага rag pipeline."""

        log_generation_pipeline_event(
            logger,
            GenerationPipelineEvent(
                status=status,
                step=step,
                document_id=document_id,
                quiz_id=quiz_id,
                request_summary=summarize_generation_request(generation_request),
                metadata={} if metadata is None else metadata,
                error_code=None if error is None else getattr(error, "code", error.__class__.__name__),
            ),
        )

    @staticmethod
    def _build_repair_request(
        repair_prompt,
        response: StructuredGenerationResponse,
        validation_error: DomainValidationError,
        generation_request: GenerationRequest,
        *,
        source_text: str,
    ) -> StructuredGenerationRequest:
        """Сформировать repair-запрос к провайдеру из некорректного структурированного вывода."""

        invalid_json = json.dumps(response.content, ensure_ascii=False, indent=2, sort_keys=True)
        return StructuredGenerationRequest(
            system_prompt=repair_prompt.system_template,
            user_prompt=repair_prompt.user_template.format(
                validation_error=validation_error.message,
                question_count=generation_request.question_count,
                language=generation_request.language,
                difficulty=generation_request.difficulty,
                quiz_type=generation_request.quiz_type,
                question_type_policy=render_question_type_policy(generation_request),
                question_type_rules=render_question_type_rules(generation_request),
                source_text=prepare_repair_source_text(source_text),
                invalid_json=invalid_json,
            ),
            schema_name=repair_prompt.schema_name,
            schema=repair_prompt.schema,
            inference_parameters=repair_prompt.inference_parameters,
            model_name=response.model_name,
        )

    @staticmethod
    def _validate_construction_inputs(
        *,
        max_document_chars: int | None,
        chunk_size: int,
        chunk_overlap: int,
        top_k: int,
        max_context_chars: int,
    ) -> None:
        """Отклонить некорректные параметры создания orchestrator."""

        if max_document_chars is not None and max_document_chars <= 0:
            raise ValueError("max_document_chars must be positive when provided")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be zero or greater")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if max_context_chars <= 0:
            raise ValueError("max_context_chars must be positive")
