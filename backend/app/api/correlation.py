"""Вспомогательные средства correlation ID для логирования в области запроса."""

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
    """Установить фабрику лог-записей, добавляющую correlation ID запроса."""

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
    """Привязать один correlation ID к текущему контексту."""

    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str]) -> None:
    """Сбросить текущий контекст correlation ID."""

    _correlation_id.reset(token)


def get_correlation_id() -> str:
    """Вернуть correlation ID, привязанный к текущему контексту."""

    return _correlation_id.get()
