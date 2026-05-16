"""Unit tests for app/services/cache/session_store.py.

Tests use AsyncMock to simulate Redis — no real Redis instance needed.

Contracts verified:
- create: stores JSON with TTL, raises ValueError if session already exists
- get: returns deserialized dict or None for missing/expired sessions
- update: refreshes TTL, raises KeyError if session not found
- delete: removes key, no-op on missing
- list_by_user: scans namespace prefix and filters by user_id
- Key namespacing: keys are prefixed as <namespace>:<session_id>
- TTL: default 24h (86_400s), configurable
"""

from __future__ import annotations

import contextlib
import json
from unittest.mock import AsyncMock

import pytest

from app.services.cache.session_store import _DEFAULT_TTL_SECONDS, SessionStore

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_redis(**overrides) -> AsyncMock:
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    for attr, val in overrides.items():
        setattr(redis, attr, val)
    return redis


SAMPLE_DATA = {
    "session_id": "abc-123",
    "user_id": "user-456",
    "status": "active",
    "stage": "lectio",
}


# ── create ────────────────────────────────────────────────────────────────────


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_new_session(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="lectio")
        await store.create("abc-123", SAMPLE_DATA)
        redis.setex.assert_awaited_once()
        args = redis.setex.call_args[0]
        assert args[0] == "lectio:abc-123"
        assert args[1] == _DEFAULT_TTL_SECONDS
        assert json.loads(args[2]) == SAMPLE_DATA

    @pytest.mark.asyncio
    async def test_raises_value_error_if_already_exists(self):
        redis = _make_redis(exists=AsyncMock(return_value=1))
        store = SessionStore(redis, namespace="lectio")
        with pytest.raises(ValueError, match="already exists"):
            await store.create("abc-123", SAMPLE_DATA)
        redis.setex.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_uses_namespace_prefix(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="examen")
        await store.create("session-1", SAMPLE_DATA)
        key = redis.setex.call_args[0][0]
        assert key.startswith("examen:")

    @pytest.mark.asyncio
    async def test_custom_ttl_applied(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="test", ttl=3600)
        await store.create("s1", SAMPLE_DATA)
        ttl = redis.setex.call_args[0][1]
        assert ttl == 3600


# ── get ───────────────────────────────────────────────────────────────────────


class TestGet:
    @pytest.mark.asyncio
    async def test_returns_deserialized_dict(self):
        redis = _make_redis(get=AsyncMock(return_value=json.dumps(SAMPLE_DATA)))
        store = SessionStore(redis, namespace="lectio")
        result = await store.get("abc-123")
        assert result == SAMPLE_DATA

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_session(self):
        redis = _make_redis(get=AsyncMock(return_value=None))
        store = SessionStore(redis, namespace="lectio")
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_namespace_key(self):
        redis = _make_redis(get=AsyncMock(return_value=json.dumps(SAMPLE_DATA)))
        store = SessionStore(redis, namespace="direction")
        await store.get("sess-999")
        redis.get.assert_awaited_with("direction:sess-999")


# ── update ────────────────────────────────────────────────────────────────────


class TestUpdate:
    @pytest.mark.asyncio
    async def test_updates_existing_session(self):
        redis = _make_redis(exists=AsyncMock(return_value=1))
        store = SessionStore(redis, namespace="lectio")
        new_data = {**SAMPLE_DATA, "stage": "meditatio"}
        await store.update("abc-123", new_data)
        args = redis.setex.call_args[0]
        assert json.loads(args[2])["stage"] == "meditatio"

    @pytest.mark.asyncio
    async def test_refreshes_ttl_on_update(self):
        redis = _make_redis(exists=AsyncMock(return_value=1))
        store = SessionStore(redis, namespace="lectio", ttl=7200)
        await store.update("abc-123", SAMPLE_DATA)
        ttl = redis.setex.call_args[0][1]
        assert ttl == 7200

    @pytest.mark.asyncio
    async def test_raises_key_error_if_not_found(self):
        redis = _make_redis(exists=AsyncMock(return_value=0))
        store = SessionStore(redis, namespace="lectio")
        with pytest.raises(KeyError):
            await store.update("missing", SAMPLE_DATA)

    @pytest.mark.asyncio
    async def test_setex_not_called_when_missing(self):
        redis = _make_redis(exists=AsyncMock(return_value=0))
        store = SessionStore(redis, namespace="lectio")
        with contextlib.suppress(KeyError):
            await store.update("missing", SAMPLE_DATA)
        redis.setex.assert_not_awaited()


# ── delete ────────────────────────────────────────────────────────────────────


class TestDelete:
    @pytest.mark.asyncio
    async def test_deletes_existing_session(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="lectio")
        await store.delete("abc-123")
        redis.delete.assert_awaited_with("lectio:abc-123")

    @pytest.mark.asyncio
    async def test_delete_is_noop_for_missing(self):
        redis = _make_redis(delete=AsyncMock(return_value=0))
        store = SessionStore(redis, namespace="lectio")
        await store.delete("never-existed")
        redis.delete.assert_awaited_once()


# ── list_by_user ──────────────────────────────────────────────────────────────


class TestListByUser:
    @pytest.mark.asyncio
    async def test_returns_sessions_for_user(self):
        user_sessions = [
            {**SAMPLE_DATA, "session_id": "s1", "user_id": "user-A"},
            {**SAMPLE_DATA, "session_id": "s2", "user_id": "user-B"},
            {**SAMPLE_DATA, "session_id": "s3", "user_id": "user-A"},
        ]

        async def _scan_iter(pattern):
            for s in user_sessions:
                yield f"lectio:{s['session_id']}"

        async def _get(key):
            sid = key.split(":")[1]
            for s in user_sessions:
                if s["session_id"] == sid:
                    return json.dumps(s)
            return None

        redis = _make_redis()
        redis.scan_iter = _scan_iter
        redis.get = _get

        store = SessionStore(redis, namespace="lectio")
        results = await store.list_by_user("user-A")
        assert len(results) == 2
        assert all(s["user_id"] == "user-A" for s in results)

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unknown_user(self):
        async def _scan_iter(pattern):
            yield "lectio:s1"

        async def _get(key):
            return json.dumps({**SAMPLE_DATA, "user_id": "other-user"})

        redis = _make_redis()
        redis.scan_iter = _scan_iter
        redis.get = _get

        store = SessionStore(redis, namespace="lectio")
        results = await store.list_by_user("nobody")
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_expired_keys(self):
        """Redis can return None for expired keys between SCAN and GET."""
        async def _scan_iter(pattern):
            yield "lectio:expired"

        async def _get(key):
            return None  # simulates TTL expiry between SCAN and GET

        redis = _make_redis()
        redis.scan_iter = _scan_iter
        redis.get = _get

        store = SessionStore(redis, namespace="lectio")
        results = await store.list_by_user("user-A")
        assert results == []


# ── Defaults ──────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_default_ttl_is_24_hours(self):
        assert _DEFAULT_TTL_SECONDS == 86_400

    def test_custom_namespace_preserved(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="examen")
        assert store._namespace == "examen"

    def test_custom_ttl_preserved(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="test", ttl=1800)
        assert store._ttl == 1800

    def test_key_format(self):
        redis = _make_redis()
        store = SessionStore(redis, namespace="ns")
        assert store._key("s1") == "ns:s1"
