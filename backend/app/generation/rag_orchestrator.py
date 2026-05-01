"""Retrieval-augmented generation orchestrator with bounded repair support."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Any
from typing import Callable
from typing import TypeVar

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
from backend.app.generation.context import assemble_context
from backend.app.generation.pipeline_logging import log_generation_pipeline_event
from backend.app.generation.quality import GenerationQualityChecker
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
    """Produce a deterministic retrieval query string from a generation request."""

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
    """Generate quizzes via retrieval-augmented prompts with bounded repair support."""

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

    def generate(self, document_id: str, generation_request: GenerationRequest) -> GenerationResult:
        """Run the full RAG pipeline for one document and persist the resulting quiz."""

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

        rag_response, rag_prompt_version, _, _ = self._run_pipeline_step(
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

        quiz, final_response, prompt_version = self._finalize_generation(
            document=document,
            generation_request=generation_request,
            response=rag_response,
            rag_prompt_version=rag_prompt_version,
        )
        return self._run_pipeline_step(
            step=GenerationPipelineStep.PERSIST,
            document_id=document.document_id,
            generation_request=generation_request,
            operation=lambda: self._persist_generation_result(quiz, generation_request, final_response, prompt_version),
            quiz_id=quiz.quiz_id,
            metadata_builder=summarize_generation_result,
        )

    def _load_generation_document(self, document_id: str) -> DocumentRecord:
        """Load and guard a stored document before generation."""

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
    ) -> tuple[StructuredGenerationResponse, str, int, int]:
        """Run chunk -> embed -> retrieve -> assemble -> generate, returning context metrics."""

        chunks = chunk_text(
            document.normalized_text,
            chunk_size=self._chunk_size,
            overlap=self._chunk_overlap,
        )
        if not chunks:
            raise DomainValidationError(
                f"document '{document.document_id}' has no content for retrieval"
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
        context = assemble_context(scored, max_chars=self._max_context_chars)
        if not context:
            raise DomainValidationError(
                f"retrieved context is empty for document '{document.document_id}'"
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
            ),
            schema_name=rag_prompt.schema_name,
            schema=rag_prompt.schema,
            inference_parameters={
                **rag_prompt.inference_parameters,
                **generation_request.inference_parameters,
            },
            model_name=generation_request.model_name,
        )
        response = self._provider.generate_structured(provider_request)
        return response, rag_prompt.version, len(context), len(scored)

    def _load_or_embed_chunks(
        self,
        *,
        document: DocumentRecord,
        chunks: tuple[TextChunk, ...],
    ) -> tuple[EmbeddedChunk, ...]:
        """Load cached chunk embeddings when available, otherwise embed and persist them."""

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
        """Return the cache-visible embedding model identifier."""

        return self._embedding_model_name or DEFAULT_RAG_CACHE_EMBEDDING_MODEL_NAME

    def _finalize_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        rag_prompt_version: str,
    ) -> tuple[Quiz, StructuredGenerationResponse, str]:
        """Normalize and validate the RAG response, then attempt repair if needed."""

        try:
            quiz = self._normalize_and_validate(document, generation_request, response)
        except DomainValidationError as error:
            return self._repair_generation(document, generation_request, response, error)
        return quiz, response, rag_prompt_version

    def _normalize_and_validate(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
    ) -> Quiz:
        """Normalize and validate a structured RAG response."""

        logger.info(
            "Received provider response model=%s payload=%s",
            response.model_name,
            summarize_model_payload(response.content),
        )
        quiz = replace(self._normalizer(response.content), document_id=document.document_id)
        self._quality_checker.ensure_quality(quiz, generation_request.question_count)
        return quiz

    def _repair_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        initial_error: DomainValidationError,
    ) -> tuple[Quiz, StructuredGenerationResponse, str]:
        """Attempt a bounded repair pass for invalid normalized output."""

        repair_prompt = self._prompt_registry.resolve(REPAIR_GENERATION_PROMPT_KEY)
        current_error: DomainValidationError = initial_error
        current_response = response

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
                repair_request = self._build_repair_request(repair_prompt, current_response, current_error)
                current_response = self._provider.generate_structured(repair_request)
                repaired_quiz = self._normalize_and_validate(
                    document=document,
                    generation_request=generation_request,
                    response=current_response,
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
            return repaired_quiz, current_response, repair_prompt.version

        raise current_error

    def _persist_generation_result(
        self,
        quiz: Quiz,
        generation_request: GenerationRequest,
        final_response: StructuredGenerationResponse,
        prompt_version: str,
    ) -> GenerationResult:
        """Persist the generated quiz and its generation metadata."""

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
        """Reject documents whose normalized text exceeds the configured limit."""

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
        """Run one rag pipeline step and emit structured status transitions."""

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
        """Emit one structured rag pipeline step event."""

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
    ) -> StructuredGenerationRequest:
        """Build the provider-facing repair request from invalid structured output."""

        invalid_json = json.dumps(response.content, ensure_ascii=False, indent=2, sort_keys=True)
        return StructuredGenerationRequest(
            system_prompt=repair_prompt.system_template,
            user_prompt=repair_prompt.user_template.format(
                validation_error=validation_error.message,
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
        """Reject invalid orchestrator construction parameters."""

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
