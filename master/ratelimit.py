"""Token-bucket rate limiting and a per-user cap on heavy concurrent jobs (SEC-06)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import contextmanager


class TokenBucket:
    """`capacity` requests at once, refilled at `refill_per_second`; keyed by user or address."""

    def __init__(self, capacity: float, refill_per_second: float, clock: Callable[[], float] = time.monotonic):
        self.capacity = capacity
        self.refill = refill_per_second
        self._clock = clock
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def take(self, key: str) -> tuple[bool, float]:
        """(allowed, retry_after_seconds). Retry-After is 0 when allowed."""
        now = self._clock()
        with self._lock:
            tokens, last = self._state.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill)
            if tokens >= 1:
                self._state[key] = (tokens - 1, now)
                return True, 0.0
            self._state[key] = (tokens, now)
            return False, (1 - tokens) / self.refill if self.refill > 0 else 60.0


class JobLimiter:
    """At most `limit` heavy jobs run per user; extra ones wait their turn without blocking other users."""

    def __init__(self, limit: int = 3):
        self.limit = limit
        self._active: dict[str, int] = {}
        self._cond = threading.Condition()

    def try_start(self, user: str) -> bool:
        with self._cond:
            if self._active.get(user, 0) >= self.limit:
                return False
            self._active[user] = self._active.get(user, 0) + 1
            return True

    def finish(self, user: str) -> None:
        with self._cond:
            self._active[user] = max(0, self._active.get(user, 0) - 1)
            self._cond.notify_all()

    @contextmanager
    def slot(self, user: str, wait_seconds: float = 0.0):
        deadline = time.monotonic() + wait_seconds
        with self._cond:
            while self._active.get(user, 0) >= self.limit:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("eşzamanlı iş sınırı doldu")
                self._cond.wait(remaining)
            self._active[user] = self._active.get(user, 0) + 1
        try:
            yield
        finally:
            self.finish(user)

    def active(self, user: str) -> int:
        return self._active.get(user, 0)


heavy_jobs = JobLimiter(limit=3)
