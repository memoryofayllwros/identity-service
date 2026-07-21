"""Simple in-process rate limiter for Identity auth endpoints (Phase 3)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

# key → timestamps of recent hits
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request, *, suffix: str) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"{ip}:{suffix}"


def enforce_rate_limit(
    request: Request,
    *,
    suffix: str,
    max_hits: int = 20,
    window_seconds: float = 60.0,
) -> None:
    """Raise 429 when the client exceeds max_hits within window_seconds."""
    key = _client_key(request, suffix=suffix)
    now = time.monotonic()
    bucket = _hits[key]
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= max_hits:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
        )
    bucket.append(now)


def clear_rate_limits() -> None:
    _hits.clear()
