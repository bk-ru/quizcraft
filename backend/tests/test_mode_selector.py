import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DomainValidationError
from backend.app.generation.mode_selector import DEFAULT_DIRECT_MAX_CHARS
from backend.app.generation.mode_selector import DEFAULT_RAG_MIN_CHARS
from backend.app.generation.mode_selector import select_generation_mode


def test_default_direct_max_is_fifteen_thousand() -> None:
    assert DEFAULT_DIRECT_MAX_CHARS == 15000


def test_default_rag_min_is_thirty_thousand() -> None:
    assert DEFAULT_RAG_MIN_CHARS == 30000


def test_select_returns_direct_for_small_documents() -> None:
    """Документы до 15000 символов → DIRECT"""
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=1000,
    )
    assert result is GenerationMode.DIRECT


def test_select_returns_direct_at_exactly_direct_max() -> None:
    """Документы ровно 15000 символов → DIRECT (<= порога)"""
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=DEFAULT_DIRECT_MAX_CHARS,
    )
    assert result is GenerationMode.DIRECT


def test_select_returns_direct_in_transition_zone() -> None:
    """Документы между 15000 и 30000 → DIRECT (по умолчанию быстрее)"""
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=20000,
    )
    assert result is GenerationMode.DIRECT


def test_select_returns_rag_at_exactly_rag_min() -> None:
    """Документы ровно 30000 символов → RAG (>= порога)"""
    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=DEFAULT_RAG_MIN_CHARS,
    )
    assert result is GenerationMode.RAG


def test_select_returns_rag_for_large_documents() -> None:
    """Документы от 30000 символов → RAG"""
    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=50000,
    )
    assert result is GenerationMode.RAG


def test_select_keeps_direct_for_large_documents_when_explicitly_requested() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=50000,
    )
    assert result is GenerationMode.DIRECT


def test_select_returns_direct_for_small_documents_in_auto_mode() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=1000,
    )
    assert result is GenerationMode.DIRECT


def test_select_returns_direct_at_auto_direct_max_boundary() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=DEFAULT_DIRECT_MAX_CHARS,
    )
    assert result is GenerationMode.DIRECT


def test_select_returns_direct_in_auto_transition_zone() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=20000,
    )
    assert result is GenerationMode.DIRECT


def test_select_keeps_rag_when_user_explicitly_requested_it() -> None:
    """Явно запрошенный RAG всегда используется"""
    result = select_generation_mode(
        requested_mode=GenerationMode.RAG,
        document_length_chars=10,
    )
    assert result is GenerationMode.RAG


def test_select_keeps_single_question_regen_regardless_of_size() -> None:
    """SINGLE_QUESTION_REGEN не зависит от размера документа"""
    result = select_generation_mode(
        requested_mode=GenerationMode.SINGLE_QUESTION_REGEN,
        document_length_chars=50000,
    )
    assert result is GenerationMode.SINGLE_QUESTION_REGEN


def test_select_uses_custom_thresholds() -> None:
    """Можно задать свои пороги"""
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=5000,
        direct_max_chars=4000,
        rag_min_chars=10000,
    )
    # 5000 > 4000 и 5000 < 10000 → зона между порогами → DIRECT
    assert result is GenerationMode.DIRECT


def test_select_with_custom_thresholds_promotes_to_rag() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=15000,
        direct_max_chars=4000,
        rag_min_chars=10000,
    )
    # 15000 >= 10000 → RAG
    assert result is GenerationMode.RAG


def test_select_supports_cyrillic_documents() -> None:
    """Кириллические документы правильно оцениваются по длине"""
    cyrillic_document = "Россия — большая страна. " * 1300  # ~39000 символов
    assert len(cyrillic_document) > DEFAULT_RAG_MIN_CHARS

    result = select_generation_mode(
        requested_mode=GenerationMode.AUTO,
        document_length_chars=len(cyrillic_document),
    )
    assert result is GenerationMode.RAG


def test_select_rejects_non_generation_mode_request() -> None:
    with pytest.raises(DomainValidationError, match="GenerationMode"):
        select_generation_mode(
            requested_mode="direct",  # type: ignore[arg-type]
            document_length_chars=10,
        )


def test_select_rejects_negative_document_length() -> None:
    with pytest.raises(DomainValidationError, match="document_length"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=-1,
        )


def test_select_rejects_boolean_document_length() -> None:
    with pytest.raises(DomainValidationError, match="document_length"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=True,
        )


def test_select_rejects_invalid_direct_max_chars() -> None:
    with pytest.raises(DomainValidationError, match="direct_max_chars"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=100,
            direct_max_chars=0,
        )


def test_select_rejects_boolean_direct_max_chars() -> None:
    with pytest.raises(DomainValidationError, match="direct_max_chars"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=100,
            direct_max_chars=True,  # type: ignore[arg-type]
        )


def test_select_rejects_invalid_rag_min_chars() -> None:
    with pytest.raises(DomainValidationError, match="rag_min_chars"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=100,
            rag_min_chars=0,
        )


def test_select_rejects_direct_max_not_less_than_rag_min() -> None:
    """direct_max_chars должен быть меньше rag_min_chars"""
    with pytest.raises(DomainValidationError, match="direct_max_chars must be less"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=100,
            direct_max_chars=30000,
            rag_min_chars=15000,
        )
