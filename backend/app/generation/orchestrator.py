"""Direct-generation orchestration with bounded repair support."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Any
from typing import Callable
from typing import TypeVar

from backend.app.domain.errors import DocumentTooLargeForGenerationError
from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import Quiz
from backend.app.domain.models import StructuredGenerationRequest
from backend.app.domain.models import StructuredGenerationResponse
from backend.app.domain.normalization import normalize_quiz_output
from backend.app.generation.pipeline_logging import log_generation_pipeline_event
from backend.app.generation.quality import GenerationQualityChecker
from backend.app.generation.quality import enrich_generation_error
from backend.app.generation.request_builder import DirectGenerationRequestBuilder
from backend.app.generation.safe_logging import summarize_document_payload
from backend.app.generation.safe_logging import summarize_generation_request
from backend.app.generation.safe_logging import summarize_generation_result
from backend.app.generation.safe_logging import summarize_model_payload
from backend.app.generation.status import GenerationPipelineEvent
from backend.app.generation.status import GenerationPipelineStep
from backend.app.generation.status import GenerationRunStatus
from backend.app.prompts.registry import PromptRegistry
from backend.app.prompts.registry import REPAIR_GENERATION_PROMPT_KEY

logger = logging.getLogger(__name__)
PipelineResult = TypeVar("PipelineResult")


class DirectGenerationOrchestrator:
    """Generate quizzes directly from stored documents with one bounded repair pass."""

    def __init__(
        self,
        document_repository,
        quiz_repository,
        generation_result_repository,
        request_builder: DirectGenerationRequestBuilder,
        provider,
        quality_checker: GenerationQualityChecker,
        normalizer: Callable[[dict[str, Any]], Quiz] = normalize_quiz_output,
        prompt_registry: type[PromptRegistry] = PromptRegistry,
        max_repair_attempts: int = 1,
        max_document_chars: int | None = None,
    ) -> None:
        if max_document_chars is not None and max_document_chars <= 0:
            raise ValueError("max_document_chars must be positive when provided")
        self._document_repository = document_repository
        self._quiz_repository = quiz_repository
        self._generation_result_repository = generation_result_repository
        self._request_builder = request_builder
        self._provider = provider
        self._quality_checker = quality_checker
        self._normalizer = normalizer
        self._prompt_registry = prompt_registry
        self._max_repair_attempts = max_repair_attempts
        self._max_document_chars = max_document_chars

    def generate(self, document_id: str, generation_request: GenerationRequest) -> GenerationResult:
        """Generate, repair if needed, persist, and return a quiz result."""

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

        direct_response, direct_prompt_version = self._run_pipeline_step(
            step=GenerationPipelineStep.GENERATE,
            document_id=document.document_id,
            generation_request=generation_request,
            operation=lambda: self._request_direct_generation(document, generation_request),
            metadata_builder=lambda direct_result: {
                "model_name": direct_result[0].model_name,
                "model_payload": summarize_model_payload(direct_result[0].content),
            },
        )

        quiz, final_response, prompt_version = self._finalize_generation(
            document=document,
            generation_request=generation_request,
            response=direct_response,
            direct_prompt_version=direct_prompt_version,
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
            "Starting direct generation document=%s",
            summarize_document_payload(document),
        )
        return document

    def _request_direct_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
    ) -> tuple[StructuredGenerationResponse, str]:
        """Build and send the provider request for direct generation."""

        direct_request = self._request_builder.build(document, generation_request)
        direct_prompt = self._prompt_registry.resolve(
            self._request_builder.resolve_prompt_key(generation_request)
        )
        return self._provider.generate_structured(direct_request), direct_prompt.version

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
        logger.info("Persisted generation result summary=%s", summarize_generation_result(result))
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

    def _finalize_generation(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
        direct_prompt_version: str,
    ) -> tuple[Quiz, StructuredGenerationResponse, str]:
        """Normalize and validate the direct response, then attempt repair if needed."""

        try:
            quiz = self._normalize_and_validate(document, generation_request, response)
        except DomainValidationError as error:
            return self._repair_generation(document, generation_request, response, error)
        return quiz, response, direct_prompt_version

    def _normalize_and_validate(
        self,
        document: DocumentRecord,
        generation_request: GenerationRequest,
        response: StructuredGenerationResponse,
    ) -> Quiz:
        """Normalize and validate a structured provider response."""

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
                "Repair attempt=%s validation_error=%s payload=%s",
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

        raise enrich_generation_error(current_error, len(document.normalized_text))

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
        """Run one generation step and emit structured status transitions."""

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
        """Emit one structured generation pipeline step event."""

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
