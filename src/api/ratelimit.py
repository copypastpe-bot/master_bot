"""In-memory sliding-window rate limiter for FastAPI endpoints.

No external dependencies — uses a dict of deques to track request timestamps
per key. Works correctly for a single-process deployment (single uvicorn worker).
"""

import time
from collections import deque
from typing import Callable, Optional

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window rate limiter.

    Tracks request timestamps per key in a deque. On each call, old entries
    outside the window are discarded, then the current count is checked.

    Thread-safety: asyncio is single-threaded — no lock needed.
    """

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        if key not in self._buckets:
            self._buckets[key] = deque()

        bucket = self._buckets[key]

        # Drop timestamps outside the window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_calls:
            return False

        bucket.append(now)
        return True

    def make_dependency(
        self,
        key_fn: Optional[Callable[[Request], str]] = None,
        status_code: int = 429,
        detail: str = "Too many requests. Please try again later.",
    ):
        """Return a FastAPI dependency that enforces this limiter.

        key_fn: callable(request) -> str used as the bucket key.
                Defaults to client IP extracted from X-Forwarded-For or client host.
        """
        limiter = self

        def _get_ip(request: Request) -> str:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return request.client.host if request.client else "unknown"

        resolve_key = key_fn or _get_ip

        async def dependency(request: Request) -> None:
            key = resolve_key(request)
            if not limiter.is_allowed(key):
                raise HTTPException(status_code=status_code, detail=detail)

        return dependency


# ---------------------------------------------------------------------------
# Named limiters — import these in routers
# ---------------------------------------------------------------------------

# Subscription invoice: max 5 invoices per IP per minute.
# Prevents spamming the Telegram invoice API which could get the bot rate-limited.
invoice_limiter = RateLimiter(max_calls=5, window_seconds=60)

# Broadcast send: max 2 sends per master per 5 minutes.
# A single broadcast already fans out to many clients — no need to allow rapid re-sends.
broadcast_limiter = RateLimiter(max_calls=2, window_seconds=300)

# General write operations (client create, order create, bonus): max 30 per IP per minute.
write_limiter = RateLimiter(max_calls=30, window_seconds=60)
