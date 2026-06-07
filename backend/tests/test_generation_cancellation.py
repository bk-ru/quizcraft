from __future__ import annotations

import threading
import time

import pytest

from backend.app.domain.errors import GenerationCancelledError
from backend.app.generation.cancellation import GenerationCancellationRegistry
from backend.app.generation.live_journal import GenerationEventStore
from backend.app.generation.status import GenerationPipelineEvent
from backend.app.generation.status import GenerationPipelineStep
from backend.app.generation.status import GenerationRunStatus


def test_registry_cancel_is_idempotent_and_preserves_russian_document_id() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-ru-1", document_id="документ-1")

    accepted = registry.cancel("run-ru-1")
    repeated = registry.cancel("run-ru-1")

    assert accepted is not None
    assert accepted.accepted is True
    assert accepted.status is GenerationRunStatus.CANCELLED
    assert accepted.document_id == "документ-1"
    assert repeated is not None
    assert repeated.accepted is False
    assert repeated.status is GenerationRunStatus.CANCELLED
    assert token.is_cancelled is True
    with pytest.raises(GenerationCancelledError):
        token.raise_if_cancelled()


def test_registry_invokes_callback_registered_after_cancellation() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-callback", document_id="doc-callback")
    registry.cancel("run-callback")
    calls: list[str] = []

    token.register_cancel_callback(lambda: calls.append("closed"))

    assert calls == ["closed"]


def test_registry_cleans_terminal_tombstones_by_ttl_and_limit() -> None:
    current_time = [100.0]
    registry = GenerationCancellationRegistry(
        tombstone_ttl_seconds=10,
        max_tombstones=2,
        clock=lambda: current_time[0],
    )

    first = registry.start_run("run-1", document_id="doc-1")
    registry.finish(first, GenerationRunStatus.FAILED)
    current_time[0] += 1
    second = registry.start_run("run-2", document_id="doc-2")
    registry.finish(second, GenerationRunStatus.DONE)
    current_time[0] += 1
    third = registry.start_run("run-3", document_id="doc-3")
    registry.finish(third, GenerationRunStatus.CANCELLED)

    assert registry.get_outcome("run-1") is None
    assert registry.get_outcome("run-2") is not None
    assert registry.get_outcome("run-3") is not None

    current_time[0] += 11

    assert registry.get_outcome("run-2") is None
    assert registry.get_outcome("run-3") is None


def test_registry_rejects_persistence_after_accepted_cancel() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-no-persist", document_id="doc-no-persist")
    persisted: list[str] = []
    registry.cancel("run-no-persist")

    with pytest.raises(GenerationCancelledError):
        token.commit_if_active(lambda: persisted.append("saved"))

    assert persisted == []


def test_registry_finish_remains_idempotent_after_cancel_tombstone_ttl_cleanup() -> None:
    current_time = [100.0]
    registry = GenerationCancellationRegistry(
        tombstone_ttl_seconds=10,
        clock=lambda: current_time[0],
    )
    token = registry.start_run("run-cancel-expired", document_id="doc-cancel-expired")
    registry.cancel("run-cancel-expired")
    current_time[0] += 11

    assert registry.get_outcome("run-cancel-expired") is None

    outcome = registry.finish(token, GenerationRunStatus.FAILED)

    assert outcome.status is GenerationRunStatus.CANCELLED
    assert outcome.accepted is False


def test_registry_cancel_waits_for_started_persistence_and_returns_done() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-persist-first", document_id="doc-persist-first")
    persistence_started = threading.Event()
    release_persistence = threading.Event()
    persisted: list[str] = []
    cancel_outcome = {}

    def persist() -> None:
        def save() -> None:
            persistence_started.set()
            assert release_persistence.wait(timeout=2)
            persisted.append("saved")

        token.commit_if_active(save)

    persistence_thread = threading.Thread(target=persist)
    persistence_thread.start()
    assert persistence_started.wait(timeout=2)

    cancel_thread = threading.Thread(
        target=lambda: cancel_outcome.setdefault("value", registry.cancel("run-persist-first"))
    )
    cancel_thread.start()
    time.sleep(0.05)
    assert cancel_thread.is_alive()

    release_persistence.set()
    persistence_thread.join(timeout=2)
    cancel_thread.join(timeout=2)

    assert not persistence_thread.is_alive()
    assert not cancel_thread.is_alive()
    assert persisted == ["saved"]
    assert cancel_outcome["value"] is not None
    assert cancel_outcome["value"].accepted is False
    assert cancel_outcome["value"].status is GenerationRunStatus.DONE


def test_event_store_keeps_cancelled_event_terminal_when_worker_reports_late_progress() -> None:
    store = GenerationEventStore()
    run_id = "run-cancel-journal"
    cancelled = store.append(
        run_id,
        GenerationPipelineEvent(
            status=GenerationRunStatus.CANCELLED,
            step=GenerationPipelineStep.CANCEL,
            document_id="документ-журнал",
        ),
    )

    late_progress = store.append(
        run_id,
        GenerationPipelineEvent(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.GENERATE,
            document_id="документ-журнал",
        ),
    )

    assert late_progress is cancelled
    assert store.list_events(run_id) == [cancelled]


def test_event_store_reset_allows_reused_run_id_after_terminal_cleanup() -> None:
    store = GenerationEventStore()
    run_id = "run-reused-journal"
    store.append(
        run_id,
        GenerationPipelineEvent(
            status=GenerationRunStatus.CANCELLED,
            step=GenerationPipelineStep.CANCEL,
            document_id="документ-старый",
        ),
    )

    store.reset_run(run_id)
    progress = store.append(
        run_id,
        GenerationPipelineEvent(
            status=GenerationRunStatus.RUNNING,
            step=GenerationPipelineStep.PARSE,
            document_id="документ-новый",
        ),
    )

    assert progress.event_id == 1
    assert store.list_events(run_id) == [progress]
