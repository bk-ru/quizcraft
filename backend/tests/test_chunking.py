import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.parsing.chunking import TextChunk
from backend.app.parsing.chunking import chunk_text


def test_chunk_text_returns_single_chunk_when_text_is_shorter_than_chunk_size() -> None:
    text = "Краткий русский текст про Москву."

    chunks = chunk_text(text, chunk_size=200, overlap=20)

    assert chunks == (
        TextChunk(
            chunk_id="chunk-0000",
            text=text,
            start_offset=0,
            end_offset=len(text),
        ),
    )


def test_chunk_text_splits_long_russian_text_with_deterministic_overlap() -> None:
    text = "Россия — большая страна, и её столица — Москва. " * 6
    chunk_size = 80
    overlap = 20

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    assert len(chunks) > 1
    assert chunks[0].chunk_id == "chunk-0000"
    assert chunks[-1].end_offset == len(text)
    for index, chunk in enumerate(chunks):
        assert chunk.chunk_id == f"chunk-{index:04d}"
        assert text[chunk.start_offset:chunk.end_offset] == chunk.text
        assert len(chunk.text) <= chunk_size
    step = chunk_size - overlap
    for previous_chunk, next_chunk in zip(chunks, chunks[1:], strict=False):
        assert next_chunk.start_offset - previous_chunk.start_offset == step
        if next_chunk is not chunks[-1]:
            assert next_chunk.start_offset < previous_chunk.end_offset


def test_chunk_text_preserves_cyrillic_round_trip() -> None:
    text = "Москва — столица России. " + "Привет, мир! " * 10
    chunk_size = 50
    overlap = 10

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    assert chunks[0].text.startswith("Москва")
    rejoined = chunks[0].text
    cursor = chunks[0].end_offset
    for chunk in chunks[1:]:
        assert chunk.start_offset < cursor or chunk.start_offset == cursor
        rejoined += chunk.text[cursor - chunk.start_offset:]
        cursor = chunk.end_offset
    assert rejoined == text


def test_chunk_text_returns_empty_tuple_for_empty_string() -> None:
    assert chunk_text("", chunk_size=64, overlap=8) == ()


def test_chunk_text_is_deterministic_for_repeated_calls() -> None:
    text = "Тестовый поток данных " * 12

    first_run = chunk_text(text, chunk_size=40, overlap=10)
    second_run = chunk_text(text, chunk_size=40, overlap=10)

    assert first_run == second_run


def test_chunk_text_terminates_when_chunk_reaches_text_end_without_extra_step() -> None:
    text = "abcdefghij"

    chunks = chunk_text(text, chunk_size=5, overlap=2)

    assert [chunk.text for chunk in chunks] == ["abcde", "defgh", "ghij"]
    assert chunks[-1].end_offset == len(text)


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_chunk_text_rejects_non_positive_chunk_size(chunk_size: int) -> None:
    with pytest.raises(DomainValidationError, match="chunk_size"):
        chunk_text("hello", chunk_size=chunk_size, overlap=0)


def test_chunk_text_rejects_negative_overlap() -> None:
    with pytest.raises(DomainValidationError, match="overlap"):
        chunk_text("hello", chunk_size=10, overlap=-1)


def test_chunk_text_rejects_overlap_equal_to_or_greater_than_chunk_size() -> None:
    with pytest.raises(DomainValidationError, match="overlap"):
        chunk_text("hello", chunk_size=5, overlap=5)
    with pytest.raises(DomainValidationError, match="overlap"):
        chunk_text("hello", chunk_size=5, overlap=10)


def test_chunk_text_rejects_non_string_input() -> None:
    with pytest.raises(DomainValidationError, match="text must be a string"):
        chunk_text(123, chunk_size=5, overlap=1)


def test_chunk_text_rejects_boolean_chunk_size_or_overlap() -> None:
    with pytest.raises(DomainValidationError, match="chunk_size"):
        chunk_text("hello", chunk_size=True, overlap=0)
    with pytest.raises(DomainValidationError, match="overlap"):
        chunk_text("hello", chunk_size=5, overlap=True)
