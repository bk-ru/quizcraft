"""In-memory live journal for generation pipeline events."""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import RLock
from typing import Any
from typing import Iterator

from backend.app.generation.status import GenerationPipelineEvent


_CURRENT_JOURNAL: ContextVar[tuple[str, "GenerationEventStore"] | None] = ContextVar(
    "current_generation_journal",
    default=None,
)


@dataclass(frozen=True, slots=True)
class GenerationJournalEntry:
    """A user-facing, sanitized generation event."""

    event_id: int
    created_at: float
    elapsed_ms: int
    event: GenerationPipelineEvent
    message: str

    def to_dict(self) -> dict[str, object]:
        payload = self.event.to_dict()
        payload.update(
            {
                "event_id": self.event_id,
                "created_at": self.created_at,
                "elapsed_ms": self.elapsed_ms,
                "message": self.message,
            }
        )
        return payload


class GenerationEventStore:
    """Thread-safe bounded store for live generation journals."""

    def __init__(self, *, max_events_per_run: int = 200) -> None:
        self._max_events_per_run = max_events_per_run
        self._lock = RLock()
        self._runs: dict[str, list[GenerationJournalEntry]] = {}
        self._started_at: dict[str, float] = {}
        self._next_event_id: dict[str, int] = {}

    def start_run(self, run_id: str) -> None:
        with self._lock:
            self._runs[run_id] = []
            self._started_at[run_id] = time.time()
            self._next_event_id[run_id] = 1

    def append(self, run_id: str, event: GenerationPipelineEvent) -> GenerationJournalEntry:
        with self._lock:
            if run_id not in self._runs:
                self.start_run(run_id)
            event_id = self._next_event_id[run_id]
            self._next_event_id[run_id] = event_id + 1
            created_at = time.time()
            entry = GenerationJournalEntry(
                event_id=event_id,
                created_at=created_at,
                elapsed_ms=max(0, int((created_at - self._started_at[run_id]) * 1000)),
                event=event,
                message=build_generation_journal_message(event),
            )
            events = self._runs[run_id]
            events.append(entry)
            if len(events) > self._max_events_per_run:
                del events[: len(events) - self._max_events_per_run]
            return entry

    def list_events(self, run_id: str, *, after: int = 0) -> list[GenerationJournalEntry]:
        with self._lock:
            return [entry for entry in self._runs.get(run_id, []) if entry.event_id > after]

    def is_complete(self, run_id: str) -> bool:
        with self._lock:
            for entry in self._runs.get(run_id, []):
                if entry.event.status.value == "failed":
                    return True
                if entry.event.step.value == "persist" and entry.event.status.value == "done":
                    return True
            return False


@contextmanager
def bind_generation_journal(run_id: str, store: GenerationEventStore) -> Iterator[None]:
    """Bind the current generation request to a live journal store."""

    store.start_run(run_id)
    token = _CURRENT_JOURNAL.set((run_id, store))
    try:
        yield
    finally:
        _CURRENT_JOURNAL.reset(token)


def record_generation_pipeline_event(event: GenerationPipelineEvent) -> None:
    current = _CURRENT_JOURNAL.get()
    if current is None:
        return
    run_id, store = current
    store.append(run_id, event)


def build_generation_journal_message(event: GenerationPipelineEvent) -> str:
    status = event.status.value
    step = event.step.value
    metadata = event.metadata
    request_summary = event.request_summary

    if status == "queued":
        parts = ["Генерация поставлена в очередь."]
        params = _format_params_summary(request_summary)
        if params:
            parts.append(f"Параметры: {params}.")
        mode = _format_generation_mode(request_summary)
        if mode:
            parts.append(f"Режим: {mode}.")
        return " ".join(parts)

    if status == "failed":
        if step == "repair":
            return _format_repair_message(status, metadata)
        return _failed_message(step, metadata, event.error_code)

    if step == "parse":
        if status == "running":
            return "Загружаем документ и проверяем ограничения."
        if status == "done":
            text_length = metadata.get("text_length")
            if isinstance(text_length, int):
                return f"Документ готов: {text_length:,} символов.".replace(",", " ")
            return "Документ готов к генерации."

    if step == "generate":
        if status == "running":
            return _format_generate_running(metadata)
        if status == "done":
            return _format_generate_done(metadata)

    if step == "repair":
        return _format_repair_message(status, metadata)

    if step == "persist":
        if status == "running":
            return "Сохраняем квиз."
        if status == "done":
            question_count = metadata.get("question_count")
            if isinstance(question_count, int):
                return f"Квиз сохранён: {question_count} вопросов."
            return "Квиз сохранён."

    return f"{step}: {status}"


def _format_params_summary(request_summary: dict[str, Any]) -> str:
    if not request_summary:
        return ""
    question_count = request_summary.get("question_count")
    language = request_summary.get("language")
    difficulty = request_summary.get("difficulty")
    quiz_type = request_summary.get("quiz_type")
    parts: list[str] = []
    if isinstance(question_count, int):
        parts.append(f"{question_count} вопросов")
    if isinstance(language, str) and language:
        lang_labels = {"ru": "русский", "en": "английский", "kk": "казахский"}
        parts.append(lang_labels.get(language, language))
    if isinstance(difficulty, str) and difficulty:
        diff_labels = {"easy": "лёгкая", "medium": "средняя", "hard": "сложная"}
        parts.append(f"{diff_labels.get(difficulty, difficulty)} сложность")
    if isinstance(quiz_type, str) and quiz_type:
        type_labels = {
            "single_choice": "множественный выбор",
            "true_false": "верно/неверно",
            "fill_blank": "заполнение пропусков",
            "short_answer": "короткий ответ",
            "matching": "соответствие",
        }
        parts.append(type_labels.get(quiz_type, quiz_type))
    return " · ".join(parts)


def _format_generation_mode(request_summary: dict[str, Any]) -> str | None:
    mode = request_summary.get("generation_mode")
    if not isinstance(mode, str):
        return None
    mode_labels = {"direct": "прямая генерация", "rag": "RAG (поиск по документу)"}
    return mode_labels.get(mode)


def _format_generate_running(metadata: dict[str, Any]) -> str:
    phase = metadata.get("phase")
    if phase == "prompt_preparation":
        return "Формируем запрос для модели."
    if phase == "rag_chunking":
        return "Делим документ на фрагменты."
    if phase == "rag_embedding":
        chunk_count = metadata.get("chunk_count")
        if isinstance(chunk_count, int):
            return f"Создаём embeddings для {chunk_count} фрагментов."
        return "Создаём embeddings для фрагментов документа."
    if phase == "rag_retrieval":
        retrieved_chunks = metadata.get("retrieved_chunks")
        if isinstance(retrieved_chunks, int):
            return f"Найдено {retrieved_chunks} релевантных фрагментов."
        return "Ищем релевантные фрагменты в документе."
    if phase == "rag_context":
        context_chars = metadata.get("context_chars")
        if isinstance(context_chars, int):
            return f"Контекст для модели: {context_chars:,} символов.".replace(",", " ")
        return "Собираем контекст для модели."
    if phase == "rag_request":
        return "Формируем RAG-запрос для модели."
    if phase == "awaiting_provider":
        return "Отправляем запрос провайдеру."
    if phase == "validation":
        return "Провайдер ответил, проверяем структуру результата."
    if phase == "quality_check":
        return "Проверяем качество квиза."
    return "Отправляем запрос провайдеру."


def _format_generate_done(metadata: dict[str, Any]) -> str:
    model_name = metadata.get("model_name")
    if isinstance(model_name, str) and model_name:
        return f"Провайдер ответил: модель {model_name}."
    return "Провайдер ответил, проверяем результат."


def _format_repair_message(status: str, metadata: dict[str, Any]) -> str:
    attempt = metadata.get("attempt")
    attempt_label = f" #{attempt}" if isinstance(attempt, int) else ""
    if status == "running":
        return f"Исправляем ответ модели{attempt_label}."
    if status == "done":
        return f"Ответ модели исправлен{attempt_label}."
    if status == "failed":
        initial_error_code = metadata.get("initial_error_code")
        if isinstance(initial_error_code, str) and initial_error_code:
            return f"Ответ модели не прошёл проверку: {initial_error_code}. Исправляем ответ модели{attempt_label}."
        return f"Ответ модели не прошёл проверку. Исправляем ответ модели{attempt_label}."
    return f"repair: {status}"


def _failed_message(step: str, metadata: dict[str, Any], error_code: str | None) -> str:
    step_labels = {
        "parse": "Ошибка подготовки документа. Проверьте формат и содержимое файла.",
        "generate": "Ошибка запроса к провайдеру. Проверьте, что backend, провайдер и настроенная модель доступны.",
        "repair": "Ошибка исправления ответа модели.",
        "persist": "Ошибка сохранения квиза.",
    }
    label = step_labels.get(step, f"Ошибка на этапе {step}.")
    if error_code:
        return f"{label} Код: {error_code}."
    return label
