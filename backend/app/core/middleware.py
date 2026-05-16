"""Custom middleware for Sancta Nexus.

Provides:
    - Request logging with timing
    - Rate limiting per IP (sliding window)
      • Global tier:  RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW  (default 120/60s)
      • AI tier:      AI_RATE_LIMIT_REQUESTS / AI_RATE_LIMIT_WINDOW (default 20/60s)
        Applied to /api/v1/ paths that invoke LLM (POST only).

Rate limiting strategy:
    - Redis-backed when Redis is available (works correctly across multiple
      instances and survives restarts).
    - Falls back to per-process in-memory sliding window when Redis is down.
      The fallback is fail-open: requests are allowed through.  This is
      intentional — denying all traffic on Redis failure is worse than
      temporarily relaxed rate limiting.

Client IP resolution:
    - Trusts X-Real-IP / X-Forwarded-For headers only when the connection
      originates from localhost (127.0.0.1 / ::1), i.e. from nginx.
      Direct connections to the backend port use the raw client IP.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sancta_nexus.middleware")

# Trusted proxy hosts — only these may set X-Real-IP / X-Forwarded-For.
_TRUSTED_PROXY_HOSTS = frozenset({"127.0.0.1", "::1"})

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

# Redis Lua script: atomic sliding-window counter.
# Returns 1 (allowed) or 0 (blocked).
_LUA_SLIDING_WINDOW = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])
local cutoff = now - window * 1000

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, now .. ':' .. math.random(1000000))
    redis.call('PEXPIRE', key, window * 1000)
    return 1
end
return 0
"""


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

    Uses Redis sorted-sets for atomic, multi-instance-safe counting.
    Falls back to in-process memory when Redis is unavailable (fail-open).
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
        # Fallback in-memory stores (single-process only)
        self._hits: dict[str, list[float]] = {}
        self._ai_hits: dict[str, list[float]] = {}

    # ------------------------------------------------------------------
    # IP resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Return the real client IP, only trusting proxy headers from localhost."""
        raw_host = request.client.host if request.client else "unknown"
        if raw_host in _TRUSTED_PROXY_HOSTS:
            forwarded = (
                request.headers.get("X-Real-IP")
                or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            )
            if forwarded:
                return forwarded
        return raw_host

    # ------------------------------------------------------------------
    # Redis-backed check (preferred)
    # ------------------------------------------------------------------

    async def _redis_check(self, redis, key: str, limit: int, window: int) -> bool:
        """Return True (allowed) using Redis sorted-set sliding window.

        Raises on Redis error — caller falls back to in-memory.
        """
        now_ms = int(time.time() * 1000)
        result = await redis.eval(_LUA_SLIDING_WINDOW, 1, key, now_ms, window, limit)
        return bool(result)

    # ------------------------------------------------------------------
    # In-memory fallback check
    # ------------------------------------------------------------------

    def _memory_check(
        self,
        store: dict[str, list[float]],
        key: str,
        max_req: int,
        window: int,
    ) -> bool:
        now = time.time()
        hits = [t for t in store.get(key, []) if t > now - window]
        if len(hits) >= max_req:
            return False
        hits.append(now)
        store[key] = hits
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_ai_path(self, path: str, method: str) -> bool:
        if method != "POST":
            return False
        return any(path.startswith(prefix) for prefix in _AI_PATH_PREFIXES)

    async def _check(
        self,
        request: Request,
        ip: str,
        key_prefix: str,
        limit: int,
        window: int,
        fallback_store: dict[str, list[float]],
    ) -> bool:
        """Try Redis first; fall back to in-memory on failure."""
        try:
            from app.core.dependencies import get_redis_direct

            redis = await get_redis_direct()
            key = f"rl:{key_prefix}:{ip}"
            return await self._redis_check(redis, key, limit, window)
        except Exception as exc:
            logger.debug("Rate limit Redis unavailable, using in-memory fallback: %s", exc)
            return self._memory_check(fallback_store, ip, limit, window)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Health checks and WebSocket upgrades bypass all limiting
        if path in ("/health",) or request.headers.get("upgrade"):
            return await call_next(request)

        client_ip = self._client_ip(request)

        # AI tier — stricter, checked first
        if self._is_ai_path(path, request.method):
            allowed = await self._check(
                request, client_ip, "ai", self._ai_max, self._ai_window, self._ai_hits
            )
            if not allowed:
                logger.warning("AI rate limit exceeded: ip=%s path=%s", client_ip, path)
                return Response(
                    content='{"detail":"AI rate limit exceeded. Maximum 20 AI requests per minute."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(self._ai_window)},
                )

        # Global tier
        allowed = await self._check(
            request, client_ip, "global", self._max, self._window, self._hits
        )
        if not allowed:
            logger.warning("Rate limit exceeded: ip=%s path=%s", client_ip, path)
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self._window)},
            )

        return await call_next(request)
