import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.generation.context import assemble_context
from backend.app.generation.retrieval import ScoredChunk
from backend.app.parsing.chunking import TextChunk


def make_scored_chunk(chunk_id: str, text: str, score: float, start_offset: int = 0) -> ScoredChunk:
    return ScoredChunk(
        chunk=TextChunk(
            chunk_id=chunk_id,
            text=text,
            start_offset=start_offset,
            end_offset=start_offset + len(text),
        ),
        score=score,
    )


def test_assemble_context_joins_cyrillic_chunks_in_supplied_order() -> None:
    scored_chunks = (
        make_scored_chunk("chunk-0000", "Москва — столица России.", 0.9),
        make_scored_chunk("chunk-0001", "Население Москвы — 13 миллионов.", 0.8, 30),
    )

    context = assemble_context(scored_chunks, max_chars=200)

    assert context == "Москва — столица России.\n\nНаселение Москвы — 13 миллионов."


def test_assemble_context_uses_custom_separator() -> None:
    scored_chunks = (
        make_scored_chunk("chunk-0000", "Россия", 0.9),
        make_scored_chunk("chunk-0001", "Беларусь", 0.7, 10),
    )

    context = assemble_context(scored_chunks, max_chars=64, separator=" | ")

    assert context == "Россия | Беларусь"


def test_assemble_context_stops_when_next_chunk_would_exceed_max_chars() -> None:
    scored_chunks = (
        make_scored_chunk("chunk-0000", "Россия — самая большая страна в мире.", 0.9),
        make_scored_chunk(
            "chunk-0001",
            "Москва — её столица, основанная в 1147 году.",
            0.8,
            50,
        ),
        make_scored_chunk(
            "chunk-0002",
            "Третий чанк не должен войти в контекст.",
            0.7,
            150,
        ),
    )

    context = assemble_context(scored_chunks, max_chars=85)

    assert context == "Россия — самая большая страна в мире.\n\nМосква — её столица, основанная в 1147 году."
    assert "Третий" not in context


def test_assemble_context_truncates_first_chunk_when_it_alone_exceeds_max_chars() -> None:
    long_text = "Россия очень большая страна — " + "очень-очень-очень " * 20
    scored_chunks = (make_scored_chunk("chunk-0000", long_text, 0.9),)

    context = assemble_context(scored_chunks, max_chars=30)

    assert context == long_text[:30]
    assert len(context) == 30


def test_assemble_context_returns_empty_string_for_empty_scored_chunks() -> None:
    assert assemble_context((), max_chars=100) == ""


def test_assemble_context_includes_only_first_chunk_when_separator_blocks_second() -> None:
    scored_chunks = (
        make_scored_chunk("chunk-0000", "А" * 50, 0.9),
        make_scored_chunk("chunk-0001", "Б" * 50, 0.8, 60),
    )

    context = assemble_context(scored_chunks, max_chars=55, separator="\n\n")

    assert context == "А" * 50


@pytest.mark.parametrize("max_chars", [0, -5])
def test_assemble_context_rejects_non_positive_max_chars(max_chars: int) -> None:
    with pytest.raises(DomainValidationError, match="max_chars"):
        assemble_context((), max_chars=max_chars)


def test_assemble_context_rejects_boolean_max_chars() -> None:
    with pytest.raises(DomainValidationError, match="max_chars"):
        assemble_context((), max_chars=True)


def test_assemble_context_rejects_non_string_separator() -> None:
    with pytest.raises(DomainValidationError, match="separator"):
        assemble_context((), max_chars=10, separator=123)  # type: ignore[arg-type]


def test_assemble_context_rejects_non_scored_chunk_entry() -> None:
    with pytest.raises(DomainValidationError, match="ScoredChunk"):
        assemble_context(("not-scored",), max_chars=10)  # type: ignore[arg-type]


def test_assemble_context_is_deterministic_for_repeated_calls() -> None:
    scored_chunks = (
        make_scored_chunk("chunk-0000", "Россия", 0.9),
        make_scored_chunk("chunk-0001", "Беларусь", 0.7, 10),
    )

    first = assemble_context(scored_chunks, max_chars=64)
    second = assemble_context(scored_chunks, max_chars=64)

    assert first == second
