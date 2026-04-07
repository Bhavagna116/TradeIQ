"""
utils/rate_limiter.py
---------------------
Thread-safe, in-memory sliding-window rate limiter.

Each identifier (API key or IP address) is allowed `max_requests` calls
within a rolling `window_seconds` window.

Usage:
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    allowed, retry_after = limiter.check("some-api-key")
    if not allowed:
        raise HTTPException(429, f"Retry after {retry_after}s")
"""

import logging
import os
import threading
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Allow env overrides so devs can tune without code changes
_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "5"))
_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


class RateLimiter:
    """
    Sliding-window rate limiter backed by an in-memory deque per identifier.

    Attributes:
        max_requests   : Maximum allowed calls within the window.
        window_seconds : Duration of the rolling window in seconds.
    """

    def __init__(
        self,
        max_requests: int = _MAX_REQUESTS,
        window_seconds: int = _WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Maps identifier → deque of UNIX timestamps for recent calls
        self._store: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()   # protect concurrent access
        logger.info(
            "RateLimiter initialised: max=%d req / %ds window",
            max_requests,
            window_seconds,
        )

    def check(self, identifier: str) -> tuple[bool, int]:
        """
        Records a new call for `identifier` and decides if it is allowed.

        Returns:
            (True, 0)               — request allowed.
            (False, retry_after)    — request denied; retry after N seconds.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            queue = self._store[identifier]

            # Evict timestamps outside the current window
            while queue and queue[0] < cutoff:
                queue.popleft()

            if len(queue) >= self.max_requests:
                # How long until the oldest timestamp falls out of the window
                retry_after = int(self.window_seconds - (now - queue[0])) + 1
                logger.debug(
                    "Rate limit hit for '%s': %d/%d calls in window",
                    identifier[:8],
                    len(queue),
                    self.max_requests,
                )
                return False, retry_after

            # Record this successful call
            queue.append(now)
            remaining = self.max_requests - len(queue)
            logger.debug(
                "Rate OK for '%s': %d/%d calls used (%d remaining)",
                identifier[:8],
                len(queue),
                self.max_requests,
                remaining,
            )
            return True, 0

    def get_usage(self, identifier: str) -> dict:
        """Returns current usage stats for an identifier (diagnostic helper)."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            queue = self._store[identifier]
            active = sum(1 for t in queue if t >= cutoff)
        return {
            "identifier": identifier,
            "calls_in_window": active,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining": max(0, self.max_requests - active),
        }
