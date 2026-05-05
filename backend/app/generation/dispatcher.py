"""Dispatcher orchestrator'ов генерации, маршрутизирующий между direct и rag pipeline."""

from __future__ import annotations

from dataclasses import replace

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import UnsupportedGenerationModeError
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult
from backend.app.generation.mode_selector import DEFAULT_DIRECT_MAX_CHARS
from backend.app.generation.mode_selector import DEFAULT_RAG_MIN_CHARS
from backend.app.generation.mode_selector import select_generation_mode
from backend.app.generation.orchestrator import DirectGenerationOrchestrator
from backend.app.generation.rag_orchestrator import RagGenerationOrchestrator


class GenerationOrchestratorDispatcher:
    """Маршрутизировать запрос генерации в direct или rag orchestrator.

    Dispatcher один раз загружает запрошенный документ, чтобы вычислить его нормализованную
    длину, применяет rule-based selector режима для повышения ``direct`` до ``rag``,
    когда документ превышает настроенный порог, заменяет ``generation_mode`` запроса
    разрешенным режимом и делегирует соответствующему orchestrator. ``single_question_regen``
    отклоняется, потому что у него есть собственный endpoint и orchestrator.
    """

    def __init__(
        self,
        *,
        direct_orchestrator: DirectGenerationOrchestrator,
        rag_orchestrator: RagGenerationOrchestrator,
        document_repository,
        direct_max_chars: int = DEFAULT_DIRECT_MAX_CHARS,
        rag_min_chars: int = DEFAULT_RAG_MIN_CHARS,
    ) -> None:
        if isinstance(direct_max_chars, bool) or not isinstance(direct_max_chars, int):
            raise ValueError("direct_max_chars must be a positive integer")
        if direct_max_chars <= 0:
            raise ValueError("direct_max_chars must be a positive integer")
        if isinstance(rag_min_chars, bool) or not isinstance(rag_min_chars, int):
            raise ValueError("rag_min_chars must be a positive integer")
        if rag_min_chars <= 0:
            raise ValueError("rag_min_chars must be a positive integer")
        if direct_max_chars >= rag_min_chars:
            raise ValueError("direct_max_chars must be less than rag_min_chars")
        self._direct_orchestrator = direct_orchestrator
        self._rag_orchestrator = rag_orchestrator
        self._document_repository = document_repository
        self._direct_max_chars = direct_max_chars
        self._rag_min_chars = rag_min_chars

    @property
    def direct_max_chars(self) -> int:
        """Раскрыть настроенный максимум для direct режима."""
        return self._direct_max_chars

    @property
    def rag_min_chars(self) -> int:
        """Раскрыть настроенный минимум для RAG режима."""
        return self._rag_min_chars

    def dispatch(
        self,
        document_id: str,
        generation_request: GenerationRequest,
    ) -> GenerationResult:
        """Определить эффективный режим для документа и делегировать orchestrator'у."""

        document = self._document_repository.get(document_id)
        resolved_mode = select_generation_mode(
            requested_mode=generation_request.generation_mode,
            document_length_chars=len(document.normalized_text),
            direct_max_chars=self._direct_max_chars,
            rag_min_chars=self._rag_min_chars,
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
