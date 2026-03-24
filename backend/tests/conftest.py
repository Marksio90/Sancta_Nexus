"""Shared pytest fixtures for Sancta Nexus backend tests.

Provides:
- ``mock_ai_message`` — factory for LangChain AIMessage objects
- ``mock_llm`` — patches every ChatOpenAI.ainvoke in the test session
- ``mock_redis`` — async Redis mock using AsyncMock
- ``app_client`` — async HTTPX client wired to the FastAPI app
- ``session_in_redis`` — helper to pre-seed a fake session in the mock Redis
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def make_ai_message(content: str) -> AIMessage:
    """Return a minimal AIMessage with the given text content."""
    return AIMessage(content=content)


@pytest.fixture()
def ai_prayer_json() -> str:
    return json.dumps({
        "prayer_text": "Panie Jezu, trwaj ze mną w tej chwili. Amen.",
        "tradition": "ignatian",
        "elements": ["colloquium", "petitio"],
    })


@pytest.fixture()
def ai_meditation_json() -> str:
    return json.dumps({
        "questions": [
            {"text": "Co to słowo mówi do ciebie?", "layer": "literalis", "scripture_echo": ""},
            {"text": "Jak ten tekst przemienia twoje serce?", "layer": "moralis", "scripture_echo": ""},
        ],
        "reflection_layers": {
            "literalis": "Analiza historyczna...",
            "allegoricus": "Typ chrystologiczny...",
            "moralis": "Zastosowanie etyczne...",
            "anagogicus": "Wymiar mistyczny...",
        },
        "patristic_insight": "Sw. Augustyn: Serce niespokojne...",
        "key_word": "trwaj",
    })


@pytest.fixture()
def ai_journey_text() -> str:
    return "STAGE: illumination\nPROGRESS: 45\nMILESTONE: Regularna modlitwa\nGROWTH: Kontemplacja"


@pytest.fixture()
def ai_patterns_text() -> str:
    return (
        "PATTERN: recurring_theme\nDESC: Zaufanie Bogu\nFREQ: co tydzień\nSCRIPTURE: Ps 23\n"
        "PATTERN: grace_moment\nDESC: Przełom w modlitwie\nFREQ: raz w miesiącu\nSCRIPTURE: J 15,5"
    )


# ---------------------------------------------------------------------------
# Redis mock
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_redis() -> AsyncMock:
    """Async Redis mock with get/set/setex/exists/delete operations."""
    redis = AsyncMock()
    _store: dict[str, Any] = {}

    async def _get(key: str) -> bytes | None:
        return _store.get(key)

    async def _setex(key: str, ttl: int, value: str) -> None:
        _store[key] = value.encode() if isinstance(value, str) else value

    async def _set(key: str, value: str) -> None:
        _store[key] = value.encode() if isinstance(value, str) else value

    async def _exists(key: str) -> int:
        return 1 if key in _store else 0

    async def _delete(key: str) -> None:
        _store.pop(key, None)

    async def _scan_iter(pattern: str):
        # Simple wildcard: match everything
        for key in list(_store.keys()):
            yield key.encode() if isinstance(key, str) else key

    redis.get.side_effect = _get
    redis.setex.side_effect = _setex
    redis.set.side_effect = _set
    redis.exists.side_effect = _exists
    redis.delete.side_effect = _delete
    redis.scan_iter = _scan_iter
    redis._store = _store
    return redis


@pytest.fixture()
def seeded_redis(mock_redis: AsyncMock) -> AsyncMock:
    """Redis mock pre-seeded with a lectio session for user 'test-user'."""
    session = {
        "session_id": "sess-001",
        "user_id": "test-user",
        "tradition": "ignatian",
        "status": "active",
        "created_at": "2026-01-01T12:00:00",
        "messages": [],
        "emotions": [{"timestamp": "2026-01-01T12:00:00", "primary": "peace", "vector": {}}],
        "reflections": {},
    }
    mock_redis._store["lectio:sess-001"] = json.dumps(session).encode()

    direction_session = {
        "session_id": "dir-001",
        "user_id": "test-user",
        "tradition": "ignatian",
        "status": "active",
        "created_at": "2026-01-01T12:00:00",
        "messages": [],
        "emotion_records": [],
    }
    mock_redis._store["direction:dir-001"] = json.dumps(direction_session).encode()
    return mock_redis


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def app_client(mock_redis: AsyncMock):
    """Async HTTPX client backed by the FastAPI app with Redis dependency overridden."""
    from app.main import app
    from app.core.dependencies import get_redis

    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def seeded_client(seeded_redis: AsyncMock):
    """Test client with a pre-seeded Redis session."""
    from app.main import app
    from app.core.dependencies import get_redis

    app.dependency_overrides[get_redis] = lambda: seeded_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
