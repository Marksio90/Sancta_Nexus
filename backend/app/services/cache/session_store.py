"""Redis-backed session store for Sancta Nexus.

Provides a thin async wrapper around redis.asyncio for JSON session
persistence with TTL support.  All callers pass a ``redis.asyncio.Redis``
client obtained from the FastAPI dependency injector.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Default TTL: 24 hours
_DEFAULT_TTL_SECONDS = 86_400


class SessionStore:
    """JSON session store backed by Redis.

    Each session is stored as a JSON string under the key
    ``<namespace>:<session_id>``.

    Args:
        redis: An async Redis client.
        namespace: Key prefix used to namespace sessions (e.g.
            ``"lectio"`` or ``"direction"``).
        ttl: Time-to-live in seconds for each session key. Defaults
            to 86 400 (24 h).
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        namespace: str,
        ttl: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._redis = redis
        self._namespace = namespace
        self._ttl = ttl

    # ── Helpers ───────────────────────────────────────────────────────────

    def _key(self, session_id: str) -> str:
        return f"{self._namespace}:{session_id}"

    # ── CRUD ──────────────────────────────────────────────────────────────

    async def create(self, session_id: str, data: dict[str, Any]) -> None:
        """Persist a new session, raising ``ValueError`` if it already exists."""
        key = self._key(session_id)
        if await self._redis.exists(key):
            raise ValueError(f"Session {session_id!r} already exists")
        await self._redis.setex(key, self._ttl, json.dumps(data))
        logger.debug("Created session %s/%s", self._namespace, session_id)

    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Return the session dict or ``None`` if not found / expired."""
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def update(self, session_id: str, data: dict[str, Any]) -> None:
        """Overwrite an existing session, refreshing its TTL.

        Raises ``KeyError`` if the session does not exist.
        """
        key = self._key(session_id)
        if not await self._redis.exists(key):
            raise KeyError(f"Session {session_id!r} not found")
        await self._redis.setex(key, self._ttl, json.dumps(data))
        logger.debug("Updated session %s/%s", self._namespace, session_id)

    async def delete(self, session_id: str) -> None:
        """Delete a session.  No-op if it does not exist."""
        await self._redis.delete(self._key(session_id))
        logger.debug("Deleted session %s/%s", self._namespace, session_id)

    async def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return all sessions for a given user (requires SCAN; use sparingly)."""
        pattern = f"{self._namespace}:*"
        results: list[dict[str, Any]] = []
        async for key in self._redis.scan_iter(pattern):
            raw = await self._redis.get(key)
            if raw is None:
                continue
            session = json.loads(raw)
            if session.get("user_id") == user_id:
                results.append(session)
        return results
