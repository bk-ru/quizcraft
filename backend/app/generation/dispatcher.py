"""Dispatcher orchestrator'ов генерации, маршрутизирующий между direct и rag pipeline."""

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
        """Раскрыть настроенный порог продвижения в rag для диагностики."""

        return self._rag_threshold_chars

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
