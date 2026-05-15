from __future__ import annotations

import json
from dataclasses import replace

import pytest

from backend.app.core.modes import GenerationMode
from backend.app.domain.errors import BackendError
from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import DocumentRecord
from backend.app.domain.models import Explanation
from backend.app.domain.models import GenerationRequest
from backend.app.domain.models import GenerationResult
from backend.app.domain.models import Option
from backend.app.domain.models import Question
from backend.app.domain.models import Quiz
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository
from backend.app.storage.rag_cache import FileSystemRagCacheRepository


def build_document(document_id: str = "doc-1") -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        filename="sample.txt",
        media_type="text/plain",
        file_size_bytes=128,
        normalized_text="Normalized text",
        metadata={"paragraphs": 1},
    )


def build_quiz(quiz_id: str = "quiz-1") -> Quiz:
    return Quiz(
        quiz_id=quiz_id,
        document_id="doc-1",
        title="Sample quiz",
        version=0,
        last_edited_at="",
        questions=(
            Question(
                question_id="question-1",
                prompt="What is 2 + 2?",
                options=(
                    Option(option_id="option-1", text="4"),
                    Option(option_id="option-2", text="5"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="2 plus 2 is 4."),
            ),
        ),
    )


def build_generation_result(quiz_id: str = "quiz-1") -> GenerationResult:
    return GenerationResult(
        quiz=build_quiz(quiz_id),
        request=GenerationRequest(
            question_count=1,
            language="ru",
            difficulty="medium",
            quiz_type="single_choice",
            generation_mode=GenerationMode.DIRECT,
        ),
        model_name="local-model",
        prompt_version="direct-v1",
    )


def write_json(path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape"))
def test_document_repository_rejects_traversal_keys_without_reading_outside_storage(tmp_path, unsafe_key) -> None:
    repository = FileSystemDocumentRepository(tmp_path)
    write_json(tmp_path / "escape.json", build_document().to_dict())

    with pytest.raises(RepositoryNotFoundError):
        repository.get(unsafe_key)


def test_document_repository_rejects_absolute_keys_without_reading_outside_storage(tmp_path) -> None:
    repository = FileSystemDocumentRepository(tmp_path)
    escaped_path = tmp_path / "absolute-escape.json"
    write_json(escaped_path, build_document().to_dict())

    with pytest.raises(RepositoryNotFoundError):
        repository.get(str(escaped_path.with_suffix("")))


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape"))
def test_quiz_repository_rejects_traversal_keys_without_reading_outside_storage(tmp_path, unsafe_key) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    write_json(tmp_path / "escape.json", build_quiz().to_dict())

    with pytest.raises(RepositoryNotFoundError):
        repository.get(unsafe_key)


def test_quiz_repository_rejects_absolute_keys_without_reading_outside_storage(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    escaped_path = tmp_path / "absolute-escape.json"
    write_json(escaped_path, build_quiz().to_dict())

    with pytest.raises(RepositoryNotFoundError):
        repository.get(str(escaped_path.with_suffix("")))


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape"))
def test_generation_result_repository_rejects_traversal_keys_without_reading_outside_storage(
    tmp_path,
    unsafe_key,
) -> None:
    repository = FileSystemGenerationResultRepository(tmp_path)
    write_json(tmp_path / "escape.json", build_generation_result().to_dict())

    with pytest.raises(RepositoryNotFoundError):
        repository.get(unsafe_key)


def test_generation_result_repository_rejects_absolute_keys_without_reading_outside_storage(tmp_path) -> None:
    repository = FileSystemGenerationResultRepository(tmp_path)
    escaped_path = tmp_path / "absolute-escape.json"
    write_json(escaped_path, build_generation_result().to_dict())

    with pytest.raises(RepositoryNotFoundError):
        repository.get(str(escaped_path.with_suffix("")))


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape"))
def test_rag_cache_repository_rejects_traversal_keys_without_reading_outside_storage(tmp_path, unsafe_key) -> None:
    repository = FileSystemRagCacheRepository(tmp_path)
    write_json(tmp_path / "escape.json", {"cache_key": "not-a-real-cache-entry"})

    with pytest.raises(RepositoryNotFoundError):
        repository.get(unsafe_key)


def test_rag_cache_repository_rejects_absolute_keys_without_reading_outside_storage(tmp_path) -> None:
    repository = FileSystemRagCacheRepository(tmp_path)
    escaped_path = tmp_path / "absolute-escape.json"
    write_json(escaped_path, {"cache_key": "not-a-real-cache-entry"})

    with pytest.raises(RepositoryNotFoundError):
        repository.get(str(escaped_path.with_suffix("")))


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape", "/absolute/escape"))
def test_document_repository_rejects_unsafe_keys_on_save(tmp_path, unsafe_key) -> None:
    repository = FileSystemDocumentRepository(tmp_path)

    with pytest.raises(BackendError) as error_info:
        repository.save(build_document(unsafe_key))

    assert error_info.value.code == "invalid_storage_key"


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape", "/absolute/escape"))
def test_quiz_repository_rejects_unsafe_keys_on_save(tmp_path, unsafe_key) -> None:
    repository = FileSystemQuizRepository(tmp_path)

    with pytest.raises(BackendError) as error_info:
        repository.save(build_quiz(unsafe_key))

    assert error_info.value.code == "invalid_storage_key"


@pytest.mark.parametrize("unsafe_key", ("../escape", "..\\escape", "/absolute/escape"))
def test_generation_result_repository_rejects_unsafe_keys_on_save(tmp_path, unsafe_key) -> None:
    repository = FileSystemGenerationResultRepository(tmp_path)
    result = replace(build_generation_result(), quiz=build_quiz(unsafe_key))

    with pytest.raises(BackendError) as error_info:
        repository.save(result)

    assert error_info.value.code == "invalid_storage_key"
