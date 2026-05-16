"""Custom middleware for Sancta Nexus.

Provides:
    - Request logging with timing
    - Rate limiting per IP (sliding window, in-memory)
      • Global tier:  RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW  (default 120/60s)
      • AI tier:      AI_RATE_LIMIT_REQUESTS / AI_RATE_LIMIT_WINDOW (default 20/60s)
        Applied to /api/v1/ paths that invoke LLM (POST only).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sancta_nexus.middleware")

# Prefixes that trigger the stricter AI tier (POST requests only)
_AI_PATH_PREFIXES = (
    "/api/v1/lectio-divina/run",
    "/api/v1/lectio-divina/emotion",
    "/api/v1/lectio-divina/reflection",
    "/api/v1/examen/start",
    "/api/v1/examen/step/",
    "/api/v1/examen/complete/",
    "/api/v1/reflection-assistant/session",
    "/api/v1/reflection-assistant/message",
    "/api/v1/sacraments/confession/stream",
    "/api/v1/sacraments/confession/contrition",
    "/api/v1/sacraments/confession/resolution",
    "/api/v1/sacraments/rcia/ask",
    "/api/v1/community/rosary/meditate/stream",
    "/api/v1/bible/search",
    "/api/v1/bible/ask",
    "/api/v1/voice/transcribe",
    "/api/v1/voice/synthesize",
)


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
    """Sliding-window rate limiter per client IP with two tiers.

    Global tier applies to all requests.
    AI tier applies a stricter limit to LLM-invoking POST endpoints.
    Falls back to a no-op when Redis is unavailable. For multi-instance
    production, replace _hits dicts with a Redis-backed implementation.
    """

    def __init__(
        self,
        app,
        max_requests: int = 120,
        window_seconds: int = 60,
        ai_max_requests: int = 20,
        ai_window_seconds: int = 60,
    ):
        super().__init__(app)
        self._max = max_requests
        self._window = window_seconds
        self._ai_max = ai_max_requests
        self._ai_window = ai_window_seconds
        self._hits: dict[str, list[float]] = {}
        self._ai_hits: dict[str, list[float]] = {}

    def _check(
        self,
        store: dict[str, list[float]],
        key: str,
        max_req: int,
        window: int,
    ) -> bool:
        """Return True if request is allowed; mutates store."""
        now = time.time()
        hits = [t for t in store.get(key, []) if t > now - window]
        if len(hits) >= max_req:
            return False
        hits.append(now)
        store[key] = hits
        return True

    def _is_ai_path(self, path: str, method: str) -> bool:
        if method != "POST":
            return False
        return any(path.startswith(prefix) for prefix in _AI_PATH_PREFIXES)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Health checks and WebSocket upgrades bypass all limiting
        if path in ("/health",) or request.headers.get("upgrade"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        # AI tier — check first (stricter)
        if self._is_ai_path(path, request.method) and not self._check(self._ai_hits, client_ip, self._ai_max, self._ai_window):
            logger.warning("AI rate limit exceeded: ip=%s path=%s", client_ip, path)
            return Response(
                content='{"detail":"AI rate limit exceeded. Maximum 20 AI requests per minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self._ai_window)},
            )

        # Global tier
        if not self._check(self._hits, client_ip, self._max, self._window):
            logger.warning("Rate limit exceeded: ip=%s path=%s", client_ip, path)
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self._window)},
            )

        return await call_next(request)
