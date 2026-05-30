"""Rule-based selector для разрешения auto режима генерации."""

from __future__ import annotations

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DomainValidationError

# Документы до этого размера — всегда direct (быстрее)
DEFAULT_DIRECT_MAX_CHARS = 15000
# Документы от этого размера — всегда RAG (для точности с большими текстами)
DEFAULT_RAG_MIN_CHARS = 30000


def select_generation_mode(
    *,
    requested_mode: GenerationMode,
    document_length_chars: int,
    direct_max_chars: int = DEFAULT_DIRECT_MAX_CHARS,
    rag_min_chars: int = DEFAULT_RAG_MIN_CHARS,
) -> GenerationMode:
    """Выбрать эффективный режим генерации с учетом явно запрошенного режима.

    Логика:
    - Явно запрошенные DIRECT, RAG и SINGLE_QUESTION_REGEN сохраняются
    - AUTO до direct_max_chars (по умолчанию 15000) → DIRECT
    - AUTO от rag_min_chars (по умолчанию 30000) → RAG
    - AUTO между порогами → DIRECT (по умолчанию быстрее)

    AUTO не передается в orchestrator.
    """

    _validate_selector_inputs(
        requested_mode=requested_mode,
        document_length_chars=document_length_chars,
        direct_max_chars=direct_max_chars,
        rag_min_chars=rag_min_chars,
    )

    if requested_mode is not GenerationMode.AUTO:
        return requested_mode
    if document_length_chars >= rag_min_chars:
        return GenerationMode.RAG
    if document_length_chars <= direct_max_chars:
        return GenerationMode.DIRECT
    # Зона между порогами (15000-30000): используем DIRECT по умолчанию
    return GenerationMode.DIRECT


def _validate_selector_inputs(
    *,
    requested_mode: GenerationMode,
    document_length_chars: int,
    direct_max_chars: int,
    rag_min_chars: int,
) -> None:
    """Отклонить некорректные входы selector'а контролируемыми доменными ошибками."""

    if not isinstance(requested_mode, GenerationMode):
        raise DomainValidationError("requested_mode must be a GenerationMode")
    if isinstance(document_length_chars, bool) or not isinstance(document_length_chars, int):
        raise DomainValidationError("document_length_chars must be a non-negative integer")
    if document_length_chars < 0:
        raise DomainValidationError("document_length_chars must be a non-negative integer")
    if isinstance(direct_max_chars, bool) or not isinstance(direct_max_chars, int):
        raise DomainValidationError("direct_max_chars must be a positive integer")
    if direct_max_chars <= 0:
        raise DomainValidationError("direct_max_chars must be a positive integer")
    if isinstance(rag_min_chars, bool) or not isinstance(rag_min_chars, int):
        raise DomainValidationError("rag_min_chars must be a positive integer")
    if rag_min_chars <= 0:
        raise DomainValidationError("rag_min_chars must be a positive integer")
    if direct_max_chars >= rag_min_chars:
        raise DomainValidationError("direct_max_chars must be less than rag_min_chars")
