import json

import pytest

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.generation.rag_cache import RagCacheEntry
from backend.app.generation.rag_cache import build_document_hash
from backend.app.generation.retrieval import EmbeddedChunk
from backend.app.parsing.chunking import TextChunk
from backend.app.storage.rag_cache import FileSystemRagCacheRepository


def make_embedded_chunk(
    chunk_id: str,
    text: str,
    embedding: tuple[float, ...],
    start_offset: int = 0,
) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=TextChunk(
            chunk_id=chunk_id,
            text=text,
            start_offset=start_offset,
            end_offset=start_offset + len(text),
        ),
        embedding=embedding,
    )


def make_cache_entry(document_text: str | None = None) -> RagCacheEntry:
    text = document_text or "Москва — столица России. Санкт-Петербург — культурная столица."
    return RagCacheEntry(
        document_hash=build_document_hash(text),
        chunk_size=80,
        chunk_overlap=20,
        embedding_model_name="cyrillic-embedding-model",
        embedded_chunks=(
            make_embedded_chunk("chunk-0000", "Москва — столица России.", (0.1, 0.2), 0),
            make_embedded_chunk("chunk-0001", "Санкт-Петербург — культурная столица.", (0.3, 0.4), 23),
        ),
    )


def test_build_document_hash_is_stable_for_same_cyrillic_text() -> None:
    text = "Москва — столица России. Привет, мир!"

    first_hash = build_document_hash(text)
    second_hash = build_document_hash(text)

    assert first_hash == second_hash
    assert len(first_hash) == 64
    assert first_hash != build_document_hash(text + " ")


def test_build_document_hash_rejects_non_string_input() -> None:
    with pytest.raises(DomainValidationError, match="document text"):
        build_document_hash(123)  # type: ignore[arg-type]


def test_rag_cache_repository_reports_cache_miss(tmp_path) -> None:
    repository = FileSystemRagCacheRepository(tmp_path)
    entry = make_cache_entry()

    assert repository.exists(entry.cache_key) is False
    with pytest.raises(RepositoryNotFoundError, match="rag_cache"):
        repository.get(entry.cache_key)


def test_rag_cache_repository_writes_and_reads_cyrillic_cache_entry(tmp_path) -> None:
    repository = FileSystemRagCacheRepository(tmp_path)
    entry = make_cache_entry()

    saved_entry = repository.save(entry)
    loaded_entry = repository.get(entry.cache_key)

    assert saved_entry == entry
    assert loaded_entry == entry
    assert loaded_entry.index_metadata == {
        "chunk_count": 2,
        "embedding_dimension": 2,
    }
    assert loaded_entry.embedded_chunks[0].chunk.text == "Москва — столица России."
    assert loaded_entry.embedded_chunks[1].chunk.text == "Санкт-Петербург — культурная столица."


def test_rag_cache_repository_delete_invalidates_entry(tmp_path) -> None:
    repository = FileSystemRagCacheRepository(tmp_path)
    entry = make_cache_entry()
    repository.save(entry)

    assert repository.delete(entry.cache_key) is True
    assert repository.exists(entry.cache_key) is False
    assert repository.delete(entry.cache_key) is False


def test_rag_cache_entry_cache_key_changes_when_embedding_parameters_change() -> None:
    base_entry = make_cache_entry()
    different_chunk_size = RagCacheEntry(
        document_hash=base_entry.document_hash,
        chunk_size=120,
        chunk_overlap=base_entry.chunk_overlap,
        embedding_model_name=base_entry.embedding_model_name,
        embedded_chunks=base_entry.embedded_chunks,
    )
    different_model = RagCacheEntry(
        document_hash=base_entry.document_hash,
        chunk_size=base_entry.chunk_size,
        chunk_overlap=base_entry.chunk_overlap,
        embedding_model_name="other-model",
        embedded_chunks=base_entry.embedded_chunks,
    )

    assert base_entry.cache_key != different_chunk_size.cache_key
    assert base_entry.cache_key != different_model.cache_key


def test_rag_cache_repository_rejects_malformed_cache_artifact(tmp_path) -> None:
    repository = FileSystemRagCacheRepository(tmp_path)
    entry = make_cache_entry()
    cache_path = tmp_path / "rag_cache" / f"{entry.cache_key}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"document_hash": entry.document_hash}), encoding="utf-8")

    with pytest.raises(DomainValidationError, match="malformed"):
        repository.get(entry.cache_key)
