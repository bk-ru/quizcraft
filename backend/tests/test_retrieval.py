import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.models import EmbeddingRequest
from backend.app.domain.models import EmbeddingResponse
from backend.app.generation.retrieval import EmbeddedChunk
from backend.app.generation.retrieval import InMemoryVectorIndex
from backend.app.generation.retrieval import ScoredChunk
from backend.app.generation.retrieval import embed_chunks
from backend.app.parsing.chunking import TextChunk


class FakeEmbeddingProvider:
    """Stub provider capturing embedding requests and returning canned vectors."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]], model_name: str = "fake-embed") -> None:
        self._vectors_by_text = vectors_by_text
        self._model_name = model_name
        self.requests: list[EmbeddingRequest] = []

    def healthcheck(self):
        raise AssertionError("healthcheck should not be called by retrieval tests")

    def generate_structured(self, request):
        raise AssertionError("generate_structured should not be called by retrieval tests")

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.requests.append(request)
        try:
            vectors = tuple(self._vectors_by_text[text] for text in request.texts)
        except KeyError as error:
            raise AssertionError(f"unexpected text passed to fake provider: {error.args[0]!r}") from error
        return EmbeddingResponse(model_name=self._model_name, vectors=vectors)


def make_chunk(chunk_id: str, text: str, start_offset: int = 0) -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        text=text,
        start_offset=start_offset,
        end_offset=start_offset + len(text),
    )


def test_embed_chunks_returns_embedded_chunks_for_cyrillic_inputs() -> None:
    chunks = (
        make_chunk("chunk-0000", "Москва — столица России.", 0),
        make_chunk("chunk-0001", "Санкт-Петербург — северная столица.", 24),
    )
    provider = FakeEmbeddingProvider(
        {
            "Москва — столица России.": (1.0, 0.0, 0.0),
            "Санкт-Петербург — северная столица.": (0.0, 1.0, 0.0),
        }
    )

    embedded = embed_chunks(chunks, provider=provider, model_name="cyrillic-embed")

    assert len(embedded) == 2
    assert embedded[0].chunk is chunks[0]
    assert embedded[0].embedding == (1.0, 0.0, 0.0)
    assert embedded[1].chunk is chunks[1]
    assert embedded[1].embedding == (0.0, 1.0, 0.0)
    assert provider.requests == [
        EmbeddingRequest(
            texts=("Москва — столица России.", "Санкт-Петербург — северная столица."),
            model_name="cyrillic-embed",
        )
    ]


def test_embed_chunks_returns_empty_tuple_for_empty_chunks() -> None:
    provider = FakeEmbeddingProvider({})

    embedded = embed_chunks((), provider=provider)

    assert embedded == ()
    assert provider.requests == []


def test_embed_chunks_batches_requests_by_batch_size() -> None:
    chunks = tuple(make_chunk(f"chunk-{i:04d}", f"Текст {i}", i * 10) for i in range(5))
    provider = FakeEmbeddingProvider(
        {chunk.text: (float(index), 0.0) for index, chunk in enumerate(chunks)}
    )

    embedded = embed_chunks(chunks, provider=provider, batch_size=2)

    assert len(embedded) == 5
    assert [request.texts for request in provider.requests] == [
        ("Текст 0", "Текст 1"),
        ("Текст 2", "Текст 3"),
        ("Текст 4",),
    ]


def test_embed_chunks_rejects_non_positive_batch_size() -> None:
    with pytest.raises(DomainValidationError, match="batch_size"):
        embed_chunks((), provider=FakeEmbeddingProvider({}), batch_size=0)


def test_embed_chunks_rejects_boolean_batch_size() -> None:
    with pytest.raises(DomainValidationError, match="batch_size"):
        embed_chunks((), provider=FakeEmbeddingProvider({}), batch_size=True)


def test_embed_chunks_rejects_non_text_chunk() -> None:
    provider = FakeEmbeddingProvider({})
    with pytest.raises(DomainValidationError, match="TextChunk"):
        embed_chunks(("not-a-chunk",), provider=provider)  # type: ignore[arg-type]


def test_in_memory_vector_index_search_orders_by_descending_similarity() -> None:
    chunks = (
        make_chunk("chunk-0000", "Москва — столица России.", 0),
        make_chunk("chunk-0001", "Питер — культурная столица.", 100),
        make_chunk("chunk-0002", "Кемерово — сибирский город.", 200),
    )
    embedded = (
        EmbeddedChunk(chunk=chunks[0], embedding=(1.0, 0.0)),
        EmbeddedChunk(chunk=chunks[1], embedding=(0.9, 0.1)),
        EmbeddedChunk(chunk=chunks[2], embedding=(0.0, 1.0)),
    )
    index = InMemoryVectorIndex(embedded)

    results = index.search((1.0, 0.0), top_k=2)

    assert [scored.chunk.chunk_id for scored in results] == ["chunk-0000", "chunk-0001"]
    assert results[0].score > results[1].score


def test_in_memory_vector_index_search_breaks_ties_by_insertion_order() -> None:
    chunks = (
        make_chunk("chunk-0000", "Россия", 0),
        make_chunk("chunk-0001", "Москва", 50),
    )
    embedded = (
        EmbeddedChunk(chunk=chunks[0], embedding=(1.0, 0.0)),
        EmbeddedChunk(chunk=chunks[1], embedding=(1.0, 0.0)),
    )
    index = InMemoryVectorIndex(embedded)

    results = index.search((1.0, 0.0), top_k=2)

    assert [scored.chunk.chunk_id for scored in results] == ["chunk-0000", "chunk-0001"]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(1.0)


def test_in_memory_vector_index_returns_empty_tuple_when_index_is_empty() -> None:
    index = InMemoryVectorIndex(())

    assert index.search((1.0,), top_k=3) == ()
    assert len(index) == 0
    assert index.dimension == 0


def test_in_memory_vector_index_returns_zero_score_for_zero_query_vector() -> None:
    chunk = make_chunk("chunk-0000", "Москва", 0)
    index = InMemoryVectorIndex(
        (EmbeddedChunk(chunk=chunk, embedding=(1.0, 0.0)),)
    )

    results = index.search((0.0, 0.0), top_k=1)

    assert results == (ScoredChunk(chunk=chunk, score=0.0),)


def test_in_memory_vector_index_clamps_top_k_to_index_size() -> None:
    chunks = (
        make_chunk("chunk-0000", "Россия"),
        make_chunk("chunk-0001", "Беларусь", 10),
    )
    embedded = (
        EmbeddedChunk(chunk=chunks[0], embedding=(1.0, 0.0)),
        EmbeddedChunk(chunk=chunks[1], embedding=(0.0, 1.0)),
    )
    index = InMemoryVectorIndex(embedded)

    results = index.search((1.0, 0.0), top_k=10)

    assert len(results) == 2


def test_in_memory_vector_index_rejects_mixed_dimension_embeddings() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Москва"), embedding=(1.0, 0.0)),
        EmbeddedChunk(chunk=make_chunk("chunk-0001", "Питер", 10), embedding=(1.0,)),
    )
    with pytest.raises(DomainValidationError, match="dimension"):
        InMemoryVectorIndex(embedded)


def test_in_memory_vector_index_rejects_empty_embedding_vector() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Москва"), embedding=()),
    )
    with pytest.raises(DomainValidationError, match="must not be empty"):
        InMemoryVectorIndex(embedded)


def test_in_memory_vector_index_rejects_non_embedded_chunk_entry() -> None:
    with pytest.raises(DomainValidationError, match="EmbeddedChunk"):
        InMemoryVectorIndex(("not-embedded",))  # type: ignore[arg-type]


def test_in_memory_vector_index_rejects_query_vector_dimension_mismatch() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Москва"), embedding=(1.0, 0.0)),
    )
    index = InMemoryVectorIndex(embedded)

    with pytest.raises(DomainValidationError, match="dimension"):
        index.search((1.0,), top_k=1)


def test_in_memory_vector_index_rejects_non_positive_top_k() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Москва"), embedding=(1.0,)),
    )
    index = InMemoryVectorIndex(embedded)

    with pytest.raises(DomainValidationError, match="top_k"):
        index.search((1.0,), top_k=0)


def test_in_memory_vector_index_rejects_boolean_top_k() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Москва"), embedding=(1.0,)),
    )
    index = InMemoryVectorIndex(embedded)

    with pytest.raises(DomainValidationError, match="top_k"):
        index.search((1.0,), top_k=True)


def test_in_memory_vector_index_rejects_string_query_vector() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Москва"), embedding=(1.0,)),
    )
    index = InMemoryVectorIndex(embedded)

    with pytest.raises(DomainValidationError, match="query_vector"):
        index.search("1.0", top_k=1)  # type: ignore[arg-type]


def test_in_memory_vector_index_search_is_deterministic_for_repeated_calls() -> None:
    embedded = (
        EmbeddedChunk(chunk=make_chunk("chunk-0000", "Россия"), embedding=(1.0, 0.0)),
        EmbeddedChunk(chunk=make_chunk("chunk-0001", "Беларусь", 10), embedding=(0.0, 1.0)),
    )
    index = InMemoryVectorIndex(embedded)

    first = index.search((1.0, 0.0), top_k=2)
    second = index.search((1.0, 0.0), top_k=2)

    assert first == second
