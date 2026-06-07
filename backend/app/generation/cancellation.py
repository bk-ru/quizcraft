"""Thread-safe lifecycle отмены generation run."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Event
from threading import RLock
from typing import Iterator
from typing import Protocol
from typing import TypeVar

from backend.app.domain.errors import GenerationCancelledError
from backend.app.domain.errors import GenerationRunConflictError
from backend.app.generation.status import GenerationRunStatus

logger = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")


class GenerationCancellationControl(Protocol):
    """Контракт cooperative cancellation для pipeline и retry."""

    @property
    def is_cancelled(self) -> bool:
        """Сообщить, была ли принята отмена."""

    def raise_if_cancelled(self) -> None:
        """Остановить дальнейшую работу после принятой отмены."""

    def wait(self, timeout: float) -> None:
        """Ожидать timeout с возможностью немедленного прерывания отменой."""

    def register_cancel_callback(self, callback: Callable[[], None]) -> None:
        """Зарегистрировать provider-specific освобождение transport resource."""

    def commit_if_active(self, callback: Callable[[], ResultT]) -> ResultT:
        """Выполнить persistence только если отмена ещё не принята."""


@dataclass(frozen=True, slots=True)
class GenerationCancellationOutcome:
    """Наблюдаемый terminal status generation run."""

    request_id: str
    document_id: str
    status: GenerationRunStatus
    accepted: bool

    def to_dict(self) -> dict[str, object]:
        """Сериализовать outcome для HTTP API."""

        return {
            "request_id": self.request_id,
            "document_id": self.document_id,
            "status": self.status.value,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class _GenerationRunTombstone:
    request_id: str
    document_id: str
    status: GenerationRunStatus
    completed_at: float


class NullGenerationCancellationToken:
    """No-op token для прямых вызовов orchestrator вне HTTP generation route."""

    @property
    def is_cancelled(self) -> bool:
        return False

    def raise_if_cancelled(self) -> None:
        return None

    def wait(self, timeout: float) -> None:
        if timeout > 0:
            time.sleep(timeout)

    def register_cancel_callback(self, callback: Callable[[], None]) -> None:
        return None

    def commit_if_active(self, callback: Callable[[], ResultT]) -> ResultT:
        return callback()


NULL_GENERATION_CANCELLATION_TOKEN = NullGenerationCancellationToken()


class GenerationCancellationToken:
    """Token одного активного generation run."""

    def __init__(
        self,
        *,
        registry: GenerationCancellationRegistry,
        request_id: str,
        document_id: str,
    ) -> None:
        self._registry = registry
        self.request_id = request_id
        self.document_id = document_id
        self._cancelled = Event()
        self._callbacks: list[Callable[[], None]] = []
        self._terminal_status: GenerationRunStatus | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise GenerationCancelledError("Генерация отменена пользователем.")

    def wait(self, timeout: float) -> None:
        self._cancelled.wait(timeout=max(0.0, timeout))
        self.raise_if_cancelled()

    def register_cancel_callback(self, callback: Callable[[], None]) -> None:
        self._registry.register_cancel_callback(self, callback)

    def commit_if_active(self, callback: Callable[[], ResultT]) -> ResultT:
        return self._registry.commit_if_active(self, callback)


class GenerationCancellationRegistry:
    """Хранить active run tokens и bounded terminal tombstones."""

    def __init__(
        self,
        *,
        tombstone_ttl_seconds: float = 15 * 60,
        max_tombstones: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if tombstone_ttl_seconds <= 0:
            raise ValueError("tombstone_ttl_seconds must be positive")
        if max_tombstones <= 0:
            raise ValueError("max_tombstones must be positive")
        self._tombstone_ttl_seconds = tombstone_ttl_seconds
        self._max_tombstones = max_tombstones
        self._clock = clock
        self._lock = RLock()
        self._active: dict[str, GenerationCancellationToken] = {}
        self._tombstones: OrderedDict[str, _GenerationRunTombstone] = OrderedDict()

    def start_run(self, request_id: str, *, document_id: str) -> GenerationCancellationToken:
        """Создать token до начала profile resolution и dispatch."""

        with self._lock:
            self._cleanup_locked()
            if request_id in self._active or request_id in self._tombstones:
                raise GenerationRunConflictError(f"generation run '{request_id}' already exists")
            token = GenerationCancellationToken(
                registry=self,
                request_id=request_id,
                document_id=document_id,
            )
            self._active[request_id] = token
            return token

    def cancel(self, request_id: str) -> GenerationCancellationOutcome | None:
        """Идемпотентно принять отмену активного run либо вернуть terminal outcome."""

        callbacks: tuple[Callable[[], None], ...] = ()
        with self._lock:
            self._cleanup_locked()
            token = self._active.get(request_id)
            if token is None:
                tombstone = self._tombstones.get(request_id)
                return None if tombstone is None else self._outcome(tombstone, accepted=False)
            token._cancelled.set()
            callbacks = tuple(token._callbacks)
            token._callbacks.clear()
            tombstone = self._complete_locked(token, GenerationRunStatus.CANCELLED)
            outcome = self._outcome(tombstone, accepted=True)
        self._invoke_callbacks(callbacks)
        return outcome

    def finish(
        self,
        token: GenerationCancellationToken,
        status: GenerationRunStatus,
    ) -> GenerationCancellationOutcome:
        """Зафиксировать terminal lifecycle, не перезаписывая уже принятый outcome."""

        if status not in {
            GenerationRunStatus.DONE,
            GenerationRunStatus.FAILED,
            GenerationRunStatus.CANCELLED,
        }:
            raise ValueError("generation run terminal status is required")
        callbacks: tuple[Callable[[], None], ...] = ()
        with self._lock:
            self._cleanup_locked()
            existing = self._tombstones.get(token.request_id)
            if existing is not None:
                return self._outcome(existing, accepted=False)
            if self._active.get(token.request_id) is not token:
                if token._terminal_status is not None:
                    return GenerationCancellationOutcome(
                        request_id=token.request_id,
                        document_id=token.document_id,
                        status=token._terminal_status,
                        accepted=False,
                    )
                raise GenerationRunConflictError(f"generation run '{token.request_id}' is not active")
            if status is GenerationRunStatus.CANCELLED:
                token._cancelled.set()
                callbacks = tuple(token._callbacks)
                token._callbacks.clear()
            tombstone = self._complete_locked(token, status)
            outcome = self._outcome(tombstone, accepted=status is GenerationRunStatus.CANCELLED)
        self._invoke_callbacks(callbacks)
        return outcome

    def get_outcome(self, request_id: str) -> GenerationCancellationOutcome | None:
        """Вернуть terminal tombstone после TTL cleanup."""

        with self._lock:
            self._cleanup_locked()
            tombstone = self._tombstones.get(request_id)
            return None if tombstone is None else self._outcome(tombstone, accepted=False)

    def register_cancel_callback(
        self,
        token: GenerationCancellationToken,
        callback: Callable[[], None],
    ) -> None:
        """Зарегистрировать callback либо немедленно вызвать его после уже принятой отмены."""

        invoke_immediately = False
        with self._lock:
            if token.is_cancelled:
                invoke_immediately = True
            elif self._active.get(token.request_id) is token:
                token._callbacks.append(callback)
        if invoke_immediately:
            self._invoke_callbacks((callback,))

    def commit_if_active(
        self,
        token: GenerationCancellationToken,
        callback: Callable[[], ResultT],
    ) -> ResultT:
        """Атомарно относительно cancel выполнить обе persistence-записи."""

        with self._lock:
            self._cleanup_locked()
            if token.is_cancelled or self._active.get(token.request_id) is not token:
                raise GenerationCancelledError("Генерация отменена пользователем.")
            result = callback()
            self._complete_locked(token, GenerationRunStatus.DONE)
            return result

    def _complete_locked(
        self,
        token: GenerationCancellationToken,
        status: GenerationRunStatus,
    ) -> _GenerationRunTombstone:
        self._active.pop(token.request_id, None)
        token._terminal_status = status
        tombstone = _GenerationRunTombstone(
            request_id=token.request_id,
            document_id=token.document_id,
            status=status,
            completed_at=self._clock(),
        )
        self._tombstones[token.request_id] = tombstone
        self._tombstones.move_to_end(token.request_id)
        self._cleanup_locked()
        return tombstone

    def _cleanup_locked(self) -> None:
        expires_before = self._clock() - self._tombstone_ttl_seconds
        while self._tombstones:
            first_request_id, first = next(iter(self._tombstones.items()))
            if first.completed_at > expires_before:
                break
            self._tombstones.pop(first_request_id)
        while len(self._tombstones) > self._max_tombstones:
            self._tombstones.popitem(last=False)

    @staticmethod
    def _outcome(
        tombstone: _GenerationRunTombstone,
        *,
        accepted: bool,
    ) -> GenerationCancellationOutcome:
        return GenerationCancellationOutcome(
            request_id=tombstone.request_id,
            document_id=tombstone.document_id,
            status=tombstone.status,
            accepted=accepted,
        )

    @staticmethod
    def _invoke_callbacks(callbacks: tuple[Callable[[], None], ...]) -> None:
        for callback in callbacks:
            try:
                callback()
            except Exception:
                logger.exception("Generation cancellation callback failed")


_CURRENT_GENERATION_CANCELLATION: ContextVar[GenerationCancellationControl | None] = ContextVar(
    "current_generation_cancellation",
    default=None,
)


@contextmanager
def bind_generation_cancellation(token: GenerationCancellationControl) -> Iterator[None]:
    """Привязать token к текущему provider/retry context."""

    context_token = _CURRENT_GENERATION_CANCELLATION.set(token)
    try:
        yield
    finally:
        _CURRENT_GENERATION_CANCELLATION.reset(context_token)


def get_current_generation_cancellation() -> GenerationCancellationControl | None:
    """Вернуть token текущего generation context для retry/provider adapters."""

    return _CURRENT_GENERATION_CANCELLATION.get()


def resolve_generation_cancellation(
    token: GenerationCancellationControl | None,
) -> GenerationCancellationControl:
    """Нормализовать optional token для orchestrator API."""

    return NULL_GENERATION_CANCELLATION_TOKEN if token is None else token
