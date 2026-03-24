"""Timing middleware — measures and logs HTTP request durations.

Adds an ``X-Response-Time-Ms`` header to every response and emits a
structured log line with method, path, status, and elapsed time.
Routes slower than SLOW_THRESHOLD_MS are logged at WARNING level.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("sancta_nexus.timing")

# Warn when a single request takes longer than this
SLOW_THRESHOLD_MS: int = 5_000


class TimingMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that records wall-clock time for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1_000

        log_fn = logger.warning if elapsed_ms > SLOW_THRESHOLD_MS else logger.info
        log_fn(
            "HTTP %s %s → %d  [%.0f ms]%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            "  ⚠ SLOW" if elapsed_ms > SLOW_THRESHOLD_MS else "",
        )

        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.0f}"
        return response
