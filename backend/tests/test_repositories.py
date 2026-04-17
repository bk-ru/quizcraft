from backend.app.domain.errors import RepositoryNotFoundError
from backend.app.domain.models import DocumentRecord, Explanation, Option, Question, Quiz
from backend.app.storage.documents import FileSystemDocumentRepository
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


def test_document_repository_persists_and_loads_document_record(tmp_path) -> None:
    repository = FileSystemDocumentRepository(tmp_path)
    document = build_document()

    repository.save(document)
    loaded = repository.get(document.document_id)

    assert loaded == document


def test_quiz_repository_persists_and_loads_quiz(tmp_path) -> None:
    repository = FileSystemQuizRepository(tmp_path)
    quiz = build_quiz()

    repository.save(quiz)
    loaded = repository.get(quiz.quiz_id)

    assert loaded == quiz


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
