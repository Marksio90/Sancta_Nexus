"""Unit tests for request middleware: logging, rate-limiting, timing.

No real HTTP server — all middleware dispatch calls use async mocks.

Contracts verified:
RequestLoggingMiddleware:
- Adds X-Process-Time-Ms header to every response
- Header value is a numeric string

RateLimitMiddleware:
- Default max_requests=100, window_seconds=60
- Stores custom max_requests / window_seconds on init
- Allows request when under the limit
- Returns 429 when limit is exceeded
- Health-check path bypasses rate limiting
- WebSocket upgrade header bypasses rate limiting
- Unknown client IP treated as "unknown"

TimingMiddleware (app/middleware/timing.py):
- SLOW_THRESHOLD_MS == 5000
- Adds X-Response-Time-Ms header to every response
- Header value is a numeric string
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.middleware.timing import SLOW_THRESHOLD_MS, TimingMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    method: str = "GET",
    path: str = "/api/v1/test",
    client_ip: str = "10.0.0.1",
    headers: dict | None = None,
) -> MagicMock:
    req = MagicMock()
    req.method = method
    req.url.path = path
    req.client = MagicMock()
    req.client.host = client_ip
    req.headers = headers or {}
    return req


def _make_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    return resp


def _call_next(response: MagicMock) -> AsyncMock:
    return AsyncMock(return_value=response)


def _make_starlette_app() -> MagicMock:
    return MagicMock()


# ===========================================================================
# RequestLoggingMiddleware
# ===========================================================================


class TestRequestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_adds_x_process_time_header(self):
        mw = RequestLoggingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        assert "X-Process-Time-Ms" in response.headers

    @pytest.mark.asyncio
    async def test_header_value_is_numeric(self):
        mw = RequestLoggingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        value = response.headers["X-Process-Time-Ms"]
        assert float(value) >= 0

    @pytest.mark.asyncio
    async def test_returns_response_from_call_next(self):
        mw = RequestLoggingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response(status_code=201)
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_works_for_post_request(self):
        mw = RequestLoggingMiddleware(_make_starlette_app())
        request = _make_request(method="POST", path="/api/v1/journal")
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        assert "X-Process-Time-Ms" in response.headers


# ===========================================================================
# RateLimitMiddleware — init defaults
# ===========================================================================


class TestRateLimitMiddlewareInit:
    def test_default_max_requests(self):
        mw = RateLimitMiddleware(_make_starlette_app())
        assert mw._max_requests == 100

    def test_default_window_seconds(self):
        mw = RateLimitMiddleware(_make_starlette_app())
        assert mw._window == 60

    def test_custom_max_requests(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=50)
        assert mw._max_requests == 50

    def test_custom_window_seconds(self):
        mw = RateLimitMiddleware(_make_starlette_app(), window_seconds=30)
        assert mw._window == 30

    def test_hits_dict_starts_empty(self):
        mw = RateLimitMiddleware(_make_starlette_app())
        assert mw._hits == {}


# ===========================================================================
# RateLimitMiddleware — dispatch logic
# ===========================================================================


class TestRateLimitMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_under_limit_returns_call_next_response(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=5)
        request = _make_request()
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_over_limit_returns_429(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=3)
        request = _make_request(client_ip="1.2.3.4")
        # Saturate the window manually
        now = time.time()
        mw._hits["1.2.3.4"] = [now, now, now]
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result.status_code == 429

    @pytest.mark.asyncio
    async def test_health_path_bypasses_limit(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=1)
        request = _make_request(path="/health", client_ip="5.6.7.8")
        now = time.time()
        mw._hits["5.6.7.8"] = [now, now, now, now, now]
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_websocket_upgrade_bypasses_limit(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=1)
        request = _make_request(
            path="/ws/rosary",
            client_ip="9.8.7.6",
            headers={"upgrade": "websocket"},
        )
        now = time.time()
        mw._hits["9.8.7.6"] = [now, now, now]
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_old_hits_cleaned_from_window(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=2, window_seconds=60)
        client = "2.3.4.5"
        # Put stale entries far in the past
        old_time = time.time() - 120
        mw._hits[client] = [old_time, old_time]
        request = _make_request(client_ip=client)
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_none_client_uses_unknown_key(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=10)
        request = _make_request(client_ip="127.0.0.1")
        request.client = None
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_429_response_has_retry_after_header(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=1, window_seconds=30)
        request = _make_request(client_ip="3.3.3.3")
        now = time.time()
        mw._hits["3.3.3.3"] = [now]
        response = _make_response()
        result = await mw.dispatch(request, _call_next(response))
        assert result.status_code == 429
        assert result.headers.get("Retry-After") == "30"

    @pytest.mark.asyncio
    async def test_hit_recorded_after_allowed_request(self):
        mw = RateLimitMiddleware(_make_starlette_app(), max_requests=10)
        client = "4.4.4.4"
        request = _make_request(client_ip=client)
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        assert len(mw._hits.get(client, [])) == 1


# ===========================================================================
# SLOW_THRESHOLD_MS constant
# ===========================================================================


class TestSlowThreshold:
    def test_slow_threshold_is_5000(self):
        assert SLOW_THRESHOLD_MS == 5_000

    def test_slow_threshold_is_int(self):
        assert isinstance(SLOW_THRESHOLD_MS, int)


# ===========================================================================
# TimingMiddleware
# ===========================================================================


class TestTimingMiddleware:
    @pytest.mark.asyncio
    async def test_adds_x_response_time_header(self):
        mw = TimingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        assert "X-Response-Time-Ms" in response.headers

    @pytest.mark.asyncio
    async def test_header_value_is_numeric_string(self):
        mw = TimingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        value = response.headers["X-Response-Time-Ms"]
        assert float(value) >= 0

    @pytest.mark.asyncio
    async def test_returns_original_response(self):
        mw = TimingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response(status_code=404)
        result = await mw.dispatch(request, _call_next(response))
        assert result is response

    @pytest.mark.asyncio
    async def test_header_format_no_decimals(self):
        mw = TimingMiddleware(_make_starlette_app())
        request = _make_request()
        response = _make_response()
        await mw.dispatch(request, _call_next(response))
        # Format string uses ":.0f" — no decimal point
        value = response.headers["X-Response-Time-Ms"]
        assert "." not in value
