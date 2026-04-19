"""Correlation ID helpers for request-scoped logging."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from contextvars import Token

REQUEST_ID_HEADER = "X-Request-ID"
_DEFAULT_CORRELATION_ID = "-"
_correlation_id: ContextVar[str] = ContextVar(
    "correlation_id",
    default=_DEFAULT_CORRELATION_ID,
)
_base_record_factory = logging.getLogRecordFactory()
_record_factory_installed = False


def install_correlation_log_record_factory() -> None:
    """Install a log-record factory that attaches the request correlation ID."""

    global _record_factory_installed
    if _record_factory_installed:
        return

    def record_factory(*args, **kwargs):
        record = _base_record_factory(*args, **kwargs)
        record.correlation_id = _correlation_id.get()
        return record

    logging.setLogRecordFactory(record_factory)
    _record_factory_installed = True


def bind_correlation_id(value: str) -> Token[str]:
    """Bind one correlation ID to the current context."""

    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str]) -> None:
    """Reset the current correlation ID context."""

    _correlation_id.reset(token)


def get_correlation_id() -> str:
    """Return the correlation ID bound to the current context."""

    return _correlation_id.get()
