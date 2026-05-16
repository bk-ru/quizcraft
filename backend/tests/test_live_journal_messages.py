"""Tests for build_generation_journal_message user-facing messages."""

from __future__ import annotations

from backend.app.generation.live_journal import build_generation_journal_message
from backend.app.generation.status import GenerationPipelineEvent
from backend.app.generation.status import GenerationPipelineStep
from backend.app.generation.status import GenerationRunStatus


def _event(
    status: GenerationRunStatus = GenerationRunStatus.RUNNING,
    step: GenerationPipelineStep = GenerationPipelineStep.GENERATE,
    metadata: dict | None = None,
    request_summary: dict | None = None,
    error_code: str | None = None,
) -> GenerationPipelineEvent:
    return GenerationPipelineEvent(
        status=status,
        step=step,
        document_id="doc-test",
        metadata=metadata or {},
        request_summary=request_summary or {},
        error_code=error_code,
    )


class TestQueuedMessages:
    def test_queued_basic(self) -> None:
        msg = build_generation_journal_message(_event(status=GenerationRunStatus.QUEUED, step=GenerationPipelineStep.PARSE))
        assert "Генерация поставлена в очередь." in msg

    def test_queued_with_params(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.QUEUED,
            step=GenerationPipelineStep.PARSE,
            request_summary={
                "question_count": 5,
                "language": "ru",
                "difficulty": "medium",
                "quiz_type": "single_choice",
            },
        ))
        assert "5 вопросов" in msg
        assert "русский" in msg
        assert "средняя сложность" in msg
        assert "множественный выбор" in msg

    def test_queued_with_direct_mode(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.QUEUED,
            step=GenerationPipelineStep.PARSE,
            request_summary={"generation_mode": "direct"},
        ))
        assert "прямая генерация" in msg

    def test_queued_with_rag_mode(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.QUEUED,
            step=GenerationPipelineStep.PARSE,
            request_summary={"generation_mode": "rag"},
        ))
        assert "RAG" in msg

    def test_queued_russian_language_labels(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.QUEUED,
            step=GenerationPipelineStep.PARSE,
            request_summary={"language": "ru"},
        ))
        assert "русский" in msg

    def test_queued_difficulty_labels(self) -> None:
        for diff, label in [("easy", "лёгкая"), ("medium", "средняя"), ("hard", "сложная")]:
            msg = build_generation_journal_message(_event(
                status=GenerationRunStatus.QUEUED,
                step=GenerationPipelineStep.PARSE,
                request_summary={"difficulty": diff},
            ))
            assert label in msg

    def test_queued_quiz_type_labels(self) -> None:
        for qtype, label in [
            ("single_choice", "множественный выбор"),
            ("true_false", "верно/неверно"),
            ("fill_blank", "заполнение пропусков"),
            ("short_answer", "короткий ответ"),
            ("matching", "соответствие"),
        ]:
            msg = build_generation_journal_message(_event(
                status=GenerationRunStatus.QUEUED,
                step=GenerationPipelineStep.PARSE,
                request_summary={"quiz_type": qtype},
            ))
            assert label in msg


class TestParseMessages:
    def test_parse_running(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.PARSE,
        ))
        assert msg == "Загружаем документ и проверяем ограничения."

    def test_parse_done_with_length(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.PARSE,
            metadata={"text_length": 1403},
        ))
        assert "1 403 символов" in msg

    def test_parse_done_without_length(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.PARSE,
        ))
        assert "Документ готов к генерации." == msg


class TestGenerateMessages:
    def test_prompt_preparation(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "prompt_preparation"},
        ))
        assert msg == "Формируем запрос для модели."

    def test_awaiting_provider(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "awaiting_provider"},
        ))
        assert msg == "Отправляем запрос провайдеру."

    def test_validation(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "validation"},
        ))
        assert msg == "Провайдер ответил, проверяем структуру результата."

    def test_quality_check(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "quality_check"},
        ))
        assert msg == "Проверяем качество квиза."

    def test_generate_done_with_model(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            metadata={"model_name": "gemma-4"},
        ))
        assert "gemma-4" in msg

    def test_generate_done_without_model(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
        ))
        assert "Провайдер ответил, проверяем результат." == msg


class TestRagMessages:
    def test_rag_chunking(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_chunking"},
        ))
        assert msg == "Делим документ на фрагменты."

    def test_rag_embedding_with_count(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_embedding", "chunk_count": 12},
        ))
        assert "12 фрагментов" in msg

    def test_rag_embedding_without_count(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_embedding"},
        ))
        assert "фрагментов документа" in msg

    def test_rag_retrieval_with_count(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_retrieval", "retrieved_chunks": 5},
        ))
        assert "5 релевантных фрагментов" in msg

    def test_rag_retrieval_without_count(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_retrieval"},
        ))
        assert "Ищем релевантные фрагменты" in msg

    def test_rag_context_with_chars(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_context", "context_chars": 3200},
        ))
        assert "3 200 символов" in msg

    def test_rag_context_without_chars(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_context"},
        ))
        assert "Собираем контекст" in msg

    def test_rag_request(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "rag_request"},
        ))
        assert msg == "Формируем RAG-запрос для модели."


class TestRepairMessages:
    def test_repair_running(self) -> None:
        msg = build_generation_journal_message(_event(
            step=GenerationPipelineStep.REPAIR,
            metadata={"attempt": 1},
        ))
        assert "Исправляем ответ модели #1." == msg

    def test_repair_done(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.REPAIR,
            metadata={"attempt": 1},
        ))
        assert "Ответ модели исправлен #1." == msg

    def test_repair_failed_with_error_code(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.REPAIR,
            metadata={"attempt": 1, "initial_error_code": "missing_title"},
        ))
        assert "не прошёл проверку: missing_title" in msg
        assert "Исправляем ответ модели #1." in msg

    def test_repair_failed_without_error_code(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.REPAIR,
            metadata={"attempt": 1},
        ))
        assert "не прошёл проверку" in msg


class TestPersistMessages:
    def test_persist_running(self) -> None:
        msg = build_generation_journal_message(_event(
            step=GenerationPipelineStep.PERSIST,
        ))
        assert msg == "Сохраняем квиз."

    def test_persist_done_with_count(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.PERSIST,
            metadata={"question_count": 5},
        ))
        assert "Квиз сохранён: 5 вопросов." == msg

    def test_persist_done_without_count(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.PERSIST,
        ))
        assert "Квиз сохранён." == msg


class TestFailedMessages:
    def test_parse_failed(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.PARSE,
        ))
        assert "Ошибка подготовки документа" in msg
        assert "Проверьте формат" in msg

    def test_generate_failed(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.GENERATE,
        ))
        assert "Ошибка запроса к провайдеру" in msg
        assert "настроенная модель" in msg

    def test_repair_failed(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.REPAIR,
        ))
        assert "не прошёл проверку" in msg or "Ошибка исправления" in msg

    def test_persist_failed(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.PERSIST,
        ))
        assert "Ошибка сохранения квиза." == msg

    def test_failed_with_error_code(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.FAILED,
            step=GenerationPipelineStep.GENERATE,
            error_code="PROVIDER_UNAVAILABLE",
        ))
        assert "Код: PROVIDER_UNAVAILABLE" in msg


class TestNoSensitiveData:
    def test_messages_do_not_contain_document_id(self) -> None:
        for step in GenerationPipelineStep:
            for status in GenerationRunStatus:
                msg = build_generation_journal_message(_event(status=status, step=step))
                assert "doc-test" not in msg, f"document_id leaked in {step}/{status}: {msg}"

    def test_messages_do_not_contain_quiz_id(self) -> None:
        event = GenerationPipelineEvent(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.PERSIST,
            document_id="doc-test",
            quiz_id="quiz-secret-123",
            metadata={"question_count": 3},
        )
        msg = build_generation_journal_message(event)
        assert "quiz-secret-123" not in msg

    def test_messages_do_not_contain_raw_prompt(self) -> None:
        msg = build_generation_journal_message(_event(
            metadata={"phase": "prompt_preparation"},
        ))
        assert "prompt" not in msg.lower() or "запрос" in msg.lower()

    def test_messages_do_not_contain_raw_document_text(self) -> None:
        msg = build_generation_journal_message(_event(
            status=GenerationRunStatus.DONE,
            step=GenerationPipelineStep.PARSE,
            metadata={"text_length": 500},
        ))
        assert "символов" in msg
