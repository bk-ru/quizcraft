from __future__ import annotations

import threading

import pytest

from backend.app.domain.errors import GenerationCancelledError
from backend.app.domain.errors import LLMTimeoutError
from backend.app.generation.cancellation import GenerationCancellationRegistry
from backend.app.generation.cancellation import bind_generation_cancellation
from backend.app.llm.retry import RetryPolicy
from backend.app.llm.retry import RetryingCaller


def test_retrying_caller_does_not_start_provider_call_after_cancel() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-retry-cancelled", document_id="doc-retry-cancelled")
    registry.cancel("run-retry-cancelled")
    calls: list[str] = []
    caller = RetryingCaller(RetryPolicy(max_retries=1))

    with pytest.raises(GenerationCancelledError):
        caller.execute(lambda: calls.append("called"), cancellation_token=token)

    assert calls == []


def test_retrying_caller_interrupts_backoff_after_cancel() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-retry-backoff", document_id="doc-retry-backoff")
    first_attempt = threading.Event()
    calls: list[str] = []
    captured_error = {}
    caller = RetryingCaller(
        RetryPolicy(max_retries=2, base_backoff_seconds=30),
    )

    def operation() -> None:
        calls.append("called")
        first_attempt.set()
        raise LLMTimeoutError("provider timeout")

    def execute() -> None:
        try:
            caller.execute(operation, cancellation_token=token)
        except Exception as error:
            captured_error["value"] = error

    thread = threading.Thread(target=execute)
    thread.start()
    assert first_attempt.wait(timeout=2)

    registry.cancel("run-retry-backoff")
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert len(calls) == 1
    assert isinstance(captured_error["value"], GenerationCancelledError)


def test_retrying_caller_uses_bound_generation_cancellation_context() -> None:
    registry = GenerationCancellationRegistry()
    token = registry.start_run("run-retry-context", document_id="doc-retry-context")
    calls: list[str] = []
    caller = RetryingCaller(
        RetryPolicy(max_retries=2, base_backoff_seconds=30),
    )

    def operation() -> None:
        calls.append("called")
        registry.cancel(token.request_id)
        raise LLMTimeoutError("provider timeout")

    with bind_generation_cancellation(token):
        with pytest.raises(GenerationCancelledError):
            caller.execute(operation)

    assert calls == ["called"]
