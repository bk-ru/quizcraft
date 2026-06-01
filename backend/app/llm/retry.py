"""Поддержка retry и timeout для вызовов провайдера."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable
from typing import TypeVar

from backend.app.domain.errors import LLMProviderError
from backend.app.generation.cancellation import GenerationCancellationControl
from backend.app.generation.cancellation import get_current_generation_cancellation

logger = logging.getLogger(__name__)

ResponseT = TypeVar("ResponseT")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Конфигурация повторов для временных сбоев провайдера."""

    max_retries: int = 2
    base_backoff_seconds: float = 0.25
    backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Отклонить некорректные значения retry policy."""

        if self.max_retries < 0:
            raise ValueError("max_retries must be zero or greater")
        if self.base_backoff_seconds < 0:
            raise ValueError("base_backoff_seconds must be zero or greater")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")

    def backoff_for_attempt(self, attempt_index: int) -> float:
        """Вернуть задержку для индекса retry-попытки."""

        return self.base_backoff_seconds * (self.backoff_multiplier ** attempt_index)


class RetryingCaller:
    """Выполнять вызовы провайдера с централизованной обработкой retry."""

    def __init__(
        self,
        retry_policy: RetryPolicy,
        sleep_function: Callable[[float], None] = time.sleep,
    ) -> None:
        self._retry_policy = retry_policy
        self._sleep = sleep_function

    def execute(
        self,
        operation: Callable[[], ResponseT],
        *,
        cancellation_token: GenerationCancellationControl | None = None,
    ) -> ResponseT:
        """Выполнить операцию, повторяя только временные ошибки провайдера."""

        token = cancellation_token or get_current_generation_cancellation()
        attempt_index = 0
        while True:
            if token is not None:
                token.raise_if_cancelled()
            try:
                return operation()
            except LLMProviderError as error:
                if not error.retryable or attempt_index >= self._retry_policy.max_retries:
                    raise
                wait_seconds = self._retry_policy.backoff_for_attempt(attempt_index)
                logger.warning(
                    "Retrying provider request after %s (%s/%s)",
                    error.code,
                    attempt_index + 1,
                    self._retry_policy.max_retries,
                )
                if token is None:
                    self._sleep(wait_seconds)
                else:
                    token.wait(wait_seconds)
                attempt_index += 1
