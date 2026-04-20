from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import DocumentRecord, Explanation, GenerationRequest, GenerationResult, Option, Question, Quiz
from backend.app.core.modes import GenerationMode
from backend.app.storage.documents import FileSystemDocumentRepository
from backend.app.storage.generation_results import FileSystemGenerationResultRepository
from backend.app.storage.quizzes import FileSystemQuizRepository


def build_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        filename="sample.txt",
        media_type="text/plain",
        file_size_bytes=128,
        normalized_text="Normalized text",
        metadata={"paragraphs": 1},
    )


def build_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-1",
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


def build_russian_document() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-ru-1",
        filename="lectures.txt",
        media_type="text/plain",
        file_size_bytes=256,
        normalized_text="Первый факт.\n\nВторой факт.",
        metadata={"paragraphs": 2},
    )


def build_russian_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz-ru-1",
        document_id="doc-ru-1",
        title="Тренировочный квиз",
        version=0,
        last_edited_at="",
        questions=(
            Question(
                question_id="question-1",
                prompt="Какой город является столицей России?",
                options=(
                    Option(option_id="option-1", text="Москва"),
                    Option(option_id="option-2", text="Казань"),
                ),
                correct_option_index=0,
                explanation=Explanation(text="Москва — столица России."),
            ),
        ),
    )


def test_document_repository_persists_and_loads_document_record(tmp_path) -> None:
    repository = FileSystemDocumentRepository(tmp_path)
    document = build_document()

    repository.save(document)
    loaded = repository.get(document.document_id)

    assert loaded == document


def test_quiz_repository_persists_and_loads_quiz(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    quiz = build_quiz()

    persisted = repository.save(quiz)
    loaded = repository.get(quiz.quiz_id)

    assert persisted.version == 1
    assert persisted.last_edited_at.endswith("Z")
    assert loaded == persisted


def test_quiz_repository_increments_version_and_refreshes_last_edit_timestamp(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    first_saved = repository.save(build_quiz())
    updated_quiz = Quiz(
        quiz_id=first_saved.quiz_id,
        document_id=first_saved.document_id,
        title="Updated title",
        version=first_saved.version,
        last_edited_at=first_saved.last_edited_at,
        questions=first_saved.questions,
    )

    second_saved = repository.save(updated_quiz)

    assert second_saved.version == 2
    assert second_saved.last_edited_at > first_saved.last_edited_at


def test_quiz_repository_raises_not_found_for_missing_quiz(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)

    try:
        repository.get("missing")
    except RepositoryNotFoundError as error:
        assert error.code == "not_found"
        assert error.entity_name == "quiz"
        assert error.entity_id == "missing"
    else:
        raise AssertionError("expected RepositoryNotFoundError for missing quiz")


def test_document_repository_preserves_cyrillic_round_trip_and_disk_text(tmp_path) -> None:
    repository = FileSystemDocumentRepository(tmp_path)
    document = build_russian_document()

    repository.save(document)

    loaded = repository.get(document.document_id)
    raw_payload = (tmp_path / "documents" / f"{document.document_id}.json").read_text(encoding="utf-8")

    assert loaded == document
    assert "Первый факт." in raw_payload
    assert "Второй факт." in raw_payload


def test_quiz_repository_preserves_cyrillic_round_trip_and_disk_text(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    quiz = build_russian_quiz()

    persisted = repository.save(quiz)
    loaded = repository.get(quiz.quiz_id)
    raw_payload = (tmp_path / "quizzes" / f"{quiz.quiz_id}.json").read_text(encoding="utf-8")

    assert loaded == persisted
    assert "Тренировочный квиз" in raw_payload
    assert "Какой город является столицей России?" in raw_payload


def test_generation_result_repository_preserves_cyrillic_round_trip_and_disk_text(tmp_path) -> None:
    repository = FileSystemGenerationResultRepository(tmp_path)
    quiz = FileSystemQuizRepository(tmp_path).save(build_russian_quiz())
    result = GenerationResult(
        quiz=quiz,
        request=GenerationRequest(
            question_count=1,
            language="русский",
            difficulty="средний",
            quiz_type="single_choice",
            generation_mode=GenerationMode.DIRECT,
        ),
        model_name="local-model",
        prompt_version="direct-v1",
    )

    repository.save(result)

    loaded = repository.get(quiz.quiz_id)
    raw_payload = (tmp_path / "generation_results" / f"{quiz.quiz_id}.json").read_text(encoding="utf-8")

    assert loaded == result
    assert "Тренировочный квиз" in raw_payload
    assert "русский" in raw_payload
