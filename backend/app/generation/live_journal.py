"""In-memory live journal for generation pipeline events."""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import RLock
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
    if status == "queued":
        return "Генерация поставлена в очередь."
    if status == "failed":
        return _failed_message(step, event.error_code)
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
            return "Отправляем запрос провайдеру."
        if status == "done":
            model_name = metadata.get("model_name")
            if isinstance(model_name, str) and model_name:
                return f"Провайдер ответил: модель {model_name}."
            return "Провайдер ответил, проверяем результат."
    if step == "repair":
        attempt = metadata.get("attempt")
        attempt_label = f" #{attempt}" if isinstance(attempt, int) else ""
        if status == "running":
            return f"Исправляем ответ модели{attempt_label}."
        if status == "done":
            return f"Ответ модели исправлен{attempt_label}."
    if step == "persist":
        if status == "running":
            return "Сохраняем квиз."
        if status == "done":
            question_count = metadata.get("question_count")
            if isinstance(question_count, int):
                return f"Квиз сохранён: {question_count} вопросов."
            return "Квиз сохранён."
    return f"{step}: {status}"


def _failed_message(step: str, error_code: str | None) -> str:
    step_labels = {
        "parse": "подготовки документа",
        "generate": "запроса к провайдеру",
        "repair": "исправления ответа",
        "persist": "сохранения квиза",
    }
    label = step_labels.get(step, step)
    if error_code:
        return f"Ошибка на этапе {label}: {error_code}."
    return f"Ошибка на этапе {label}."
