"""Retry utilities with exponential backoff and optional jitter."""

from __future__ import annotations

import random
import time
from typing import Callable, Optional, Tuple, Type, TypeVar

T = TypeVar("T")


class RetryError(RuntimeError):
    """Raised when retry attempts are exhausted."""


def retry_with_backoff(
    func: Callable[[], T],
    *,
    max_tries: int = 5,
    base: float = 0.5,
    cap: float = 60.0,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
    retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    on_retry: Optional[Callable[[BaseException, int], Optional[float]]] = None,
) -> T:
    """Execute ``func`` with retries and exponential backoff.

    Args:
        func: Callable without arguments.
        max_tries: Maximum number of attempts (>=1).
        base: Base wait time for the first retry.
        cap: Maximum wait time between retries.
        jitter: Whether to add random jitter between 0 and base seconds.
        sleep: Sleep function, injectable for tests.
        retry_exceptions: Tuple of exception classes that trigger a retry.
        on_retry: Optional callback receiving (exception, attempt_index) and
            returning an override wait time in seconds.

    Returns:
        The value returned by ``func``.

    Raises:
        RetryError: If the maximum number of retries is exhausted.
        Exception: Any non-retryable exception raised by ``func``.
    """

    if max_tries < 1:
        raise ValueError("max_tries must be >= 1")

    attempt = 0
    while attempt < max_tries:
        try:
            return func()
        except retry_exceptions as exc:  # type: ignore[misc]
            attempt += 1
            if attempt >= max_tries:
                raise RetryError("retry attempts exhausted") from exc

            wait = min(cap, base * (2 ** (attempt - 1)))
            override = on_retry(exc, attempt) if on_retry else None
            if override is not None:
                wait = max(0.0, override)
            elif jitter:
                wait += random.uniform(0.0, base)

            if wait > 0:
                sleep(wait)
        except Exception:
            raise

    raise RetryError("retry attempts exhausted")
