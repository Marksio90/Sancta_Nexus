"""Custom middleware for Sancta Nexus.

Provides:
    - Request logging with timing
    - Rate limiting per IP (sliding window via Redis)
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sancta_nexus.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter per client IP.

    Falls back to a no-op when Redis is unavailable. For production,
    replace with a Redis-backed implementation.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self._max_requests = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and WebSocket upgrades
        if request.url.path in ("/health",) or request.headers.get("upgrade"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self._window

        # Clean old entries
        hits = self._hits.get(client_ip, [])
        hits = [t for t in hits if t > cutoff]

        if len(hits) >= self._max_requests:
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self._window)},
            )

        hits.append(now)
        self._hits[client_ip] = hits
        return await call_next(request)
