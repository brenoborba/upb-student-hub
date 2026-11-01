"""Thread-safe token-bucket rate limiter, shared by the CLI and the backend."""
from __future__ import annotations

import threading
import time


class RateLimiter:
    """A token bucket that blocks callers until a token is available.

    ``rate`` is tokens per second. ``capacity`` caps the burst size and defaults
    to one minute's worth of tokens (``rate * 60``).
    """

    def __init__(self, rate: float, capacity: float | None = None):
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.rate = float(rate)
        self.capacity = float(capacity) if capacity is not None else rate * 60.0
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self.rate
            time.sleep(wait)
