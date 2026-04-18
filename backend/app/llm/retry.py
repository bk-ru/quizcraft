"""Retry and timeout support for provider calls."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable
from typing import TypeVar

from backend.app.domain.errors import LLMProviderError

logger = logging.getLogger(__name__)

ResponseT = TypeVar("ResponseT")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configuration for retrying transient provider failures."""

    max_retries: int = 2
    base_backoff_seconds: float = 0.25
    backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Reject invalid retry policy values."""

        if self.max_retries < 0:
            raise ValueError("max_retries must be zero or greater")
        if self.base_backoff_seconds < 0:
            raise ValueError("base_backoff_seconds must be zero or greater")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")

    def backoff_for_attempt(self, attempt_index: int) -> float:
        """Return the delay for a retry attempt index."""

        return self.base_backoff_seconds * (self.backoff_multiplier ** attempt_index)


class RetryingCaller:
    """Execute provider calls with centralized retry handling."""

    def __init__(
        self,
        retry_policy: RetryPolicy,
        sleep_function: Callable[[float], None] = time.sleep,
    ) -> None:
        self._retry_policy = retry_policy
        self._sleep = sleep_function

    def execute(self, operation: Callable[[], ResponseT]) -> ResponseT:
        """Run an operation, retrying only transient provider errors."""

        attempt_index = 0
        while True:
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
                self._sleep(wait_seconds)
                attempt_index += 1
