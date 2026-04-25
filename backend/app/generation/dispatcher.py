"""Generation orchestrator dispatcher routing between direct and rag pipelines."""

from __future__ import annotations

from dataclasses import replace

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult
from backend.app.generation.mode_selector import DEFAULT_RAG_THRESHOLD_CHARS
from backend.app.generation.mode_selector import select_generation_mode
from backend.app.generation.orchestrator import DirectGenerationOrchestrator
from backend.app.generation.rag_orchestrator import RagGenerationOrchestrator


class GenerationOrchestratorDispatcher:
    """Route a generation request to the direct or rag orchestrator.

    The dispatcher loads the requested document once to compute its normalized
    length, applies the rule-based mode selector to promote ``direct`` to ``rag``
    when the document exceeds the configured threshold, replaces the request's
    ``generation_mode`` with the resolved mode, and delegates to the matching
    orchestrator. ``single_question_regen`` is rejected because it has its own
    dedicated endpoint and orchestrator.
    """

    def __init__(
        self,
        *,
        direct_orchestrator: DirectGenerationOrchestrator,
        rag_orchestrator: RagGenerationOrchestrator,
        document_repository,
        rag_threshold_chars: int = DEFAULT_RAG_THRESHOLD_CHARS,
    ) -> None:
        if isinstance(rag_threshold_chars, bool) or not isinstance(rag_threshold_chars, int):
            raise ValueError("rag_threshold_chars must be a positive integer")
        if rag_threshold_chars <= 0:
            raise ValueError("rag_threshold_chars must be a positive integer")
        self._direct_orchestrator = direct_orchestrator
        self._rag_orchestrator = rag_orchestrator
        self._document_repository = document_repository
        self._rag_threshold_chars = rag_threshold_chars

    @property
    def rag_threshold_chars(self) -> int:
        """Expose the configured rag promotion threshold for diagnostics."""

        return self._rag_threshold_chars

    def dispatch(
        self,
        document_id: str,
        generation_request: GenerationRequest,
    ) -> GenerationResult:
        """Resolve the effective mode for the document and delegate to an orchestrator."""

        document = self._document_repository.get(document_id)
        resolved_mode = select_generation_mode(
            requested_mode=generation_request.generation_mode,
            document_length_chars=len(document.normalized_text),
            rag_threshold_chars=self._rag_threshold_chars,
        )
        resolved_request = (
            generation_request
            if resolved_mode is generation_request.generation_mode
            else replace(generation_request, generation_mode=resolved_mode)
        )
        if resolved_mode is GenerationMode.RAG:
            return self._rag_orchestrator.generate(document_id, resolved_request)
        if resolved_mode is GenerationMode.DIRECT:
            return self._direct_orchestrator.generate(document_id, resolved_request)
        raise UnsupportedGenerationModeError(
            f"generation dispatcher does not support mode: {resolved_mode}"
        )
