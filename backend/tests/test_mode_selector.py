import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import DomainValidationError
from backend.app.generation.mode_selector import DEFAULT_RAG_THRESHOLD_CHARS
from backend.app.generation.mode_selector import select_generation_mode


def test_default_threshold_is_six_thousand_characters() -> None:
    assert DEFAULT_RAG_THRESHOLD_CHARS == 6000


def test_select_returns_direct_when_document_fits_threshold() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=1000,
    )

    assert result is GenerationMode.DIRECT


def test_select_promotes_direct_to_rag_when_document_exceeds_threshold() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=DEFAULT_RAG_THRESHOLD_CHARS + 1,
    )

    assert result is GenerationMode.RAG


def test_select_keeps_direct_when_document_is_exactly_threshold() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=DEFAULT_RAG_THRESHOLD_CHARS,
    )

    assert result is GenerationMode.DIRECT


def test_select_keeps_rag_when_user_explicitly_requested_it_for_small_document() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.RAG,
        document_length_chars=10,
    )

    assert result is GenerationMode.RAG


def test_select_keeps_single_question_regen_regardless_of_document_size() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.SINGLE_QUESTION_REGEN,
        document_length_chars=DEFAULT_RAG_THRESHOLD_CHARS * 10,
    )

    assert result is GenerationMode.SINGLE_QUESTION_REGEN


def test_select_respects_custom_threshold() -> None:
    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
        document_length_chars=2500,
        rag_threshold_chars=2000,
    )

    assert result is GenerationMode.RAG


def test_select_supports_cyrillic_documents_by_character_length() -> None:
    cyrillic_document = "Россия — большая страна. " * 300
    assert len(cyrillic_document) > DEFAULT_RAG_THRESHOLD_CHARS

    result = select_generation_mode(
        requested_mode=GenerationMode.DIRECT,
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


def test_select_rejects_non_positive_threshold() -> None:
    with pytest.raises(DomainValidationError, match="rag_threshold"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=100,
            rag_threshold_chars=0,
        )


def test_select_rejects_boolean_threshold() -> None:
    with pytest.raises(DomainValidationError, match="rag_threshold"):
        select_generation_mode(
            requested_mode=GenerationMode.DIRECT,
            document_length_chars=100,
            rag_threshold_chars=True,
        )
