"""Integration tests for Ignatian Examen API routes.

Tests /api/v1/examen/start, /step, /session/{id}, /complete
with mocked Redis. No real DB, Redis, or LLM — everything stubbed.
"""

from __future__ import annotations

import json
import sys
import types

# ---------------------------------------------------------------------------
# Stub heavy optional deps before any app import triggers their load
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return sys.modules[name]

_jose = _stub("jose", JWTError=Exception)
_jose_jwt = _stub("jose.jwt")
_stub("neo4j", AsyncDriver=object, AsyncGraphDatabase=object, AsyncSession=object)
_qdrant = _stub("qdrant_client", AsyncQdrantClient=object, QdrantClient=object)
_qdrant.__path__ = []
_stub("qdrant_client.models", FieldCondition=object, Filter=object, MatchValue=object)
for _m in ("anthropic", "openai", "langchain_openai", "langchain_openai.chat_models", "asyncpg"):
    _stub(_m)

# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.rbac import require_authenticated
from app.main import app

# FastAPI looks up the inner callable, not the Depends wrapper.
_AUTH_DEP = require_authenticated.dependency

BASE = "/api/v1/examen"

DISCLAIMER_FRAGMENT = "Asystent refleksji"

CANONICAL_PHASES = ["gratitude", "petition", "review", "response", "resolution"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mock_user(user_id: str = "test-user") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_redis() -> AsyncMock:
    """In-memory Redis mock."""
    redis = AsyncMock()
    _store: dict[str, bytes] = {}

    async def _get(key: str):
        return _store.get(key)

    async def _setex(key: str, ttl: int, value):
        _store[key] = value.encode() if isinstance(value, str) else value

    async def _set(key: str, value):
        _store[key] = value.encode() if isinstance(value, str) else value

    async def _exists(key: str) -> int:
        return 1 if key in _store else 0

    async def _delete(key: str) -> None:
        _store.pop(key, None)

    async def _scan_iter(pattern: str):
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
    """Redis with a pre-existing examen session for 'test-user'."""
    session = {
        "session_id": "examen-001",
        "user_id": "test-user",
        "started_at": "2026-01-01T10:00:00+00:00",
        "current_phase": "gratitude",
        "phases_completed": [],
        "reflections": {},
        "ai_responses": {},
        "intention": "Za pokój w rodzinie",
    }
    mock_redis._store["examen:examen-001"] = json.dumps(session).encode()
    return mock_redis


def _mock_db_session() -> AsyncMock:
    """Return a minimal AsyncSession mock."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest_asyncio.fixture()
async def app_client(mock_redis: AsyncMock):
    from app.core.dependencies import get_db, get_redis_client
    mock_db = _mock_db_session()
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def seeded_client(seeded_redis: AsyncMock):
    from app.core.dependencies import get_db, get_redis_client
    mock_db = _mock_db_session()
    app.dependency_overrides[get_redis_client] = lambda: seeded_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def authed_client(app_client: AsyncClient):
    app.dependency_overrides[_AUTH_DEP] = lambda: _mock_user()
    yield app_client
    app.dependency_overrides.pop(_AUTH_DEP, None)


@pytest_asyncio.fixture()
async def authed_seeded_client(seeded_client: AsyncClient):
    app.dependency_overrides[_AUTH_DEP] = lambda: _mock_user()
    yield seeded_client
    app.dependency_overrides.pop(_AUTH_DEP, None)


# ---------------------------------------------------------------------------
# POST /examen/start
# ---------------------------------------------------------------------------

async def test_start_examen_requires_auth(app_client: AsyncClient):
    response = await app_client.post(f"{BASE}/start", json={})
    assert response.status_code == 401


async def test_start_examen_creates_session(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/start", json={"intention": "Pokój"})
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["current_phase"] == "gratitude"
    assert "phase_meta" in data


async def test_start_examen_disclaimer_present(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/start", json={})
    assert response.status_code == 201
    data = response.json()
    assert DISCLAIMER_FRAGMENT in data["disclaimer"]


async def test_start_examen_phase_meta_has_gratitude_info(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/start", json={})
    assert response.status_code == 201
    meta = response.json()["phase_meta"]
    assert "title" in meta
    assert "prompt_intro" in meta


async def test_start_examen_without_intention(authed_client: AsyncClient):
    """Intention is optional — should succeed with an empty body."""
    response = await authed_client.post(f"{BASE}/start", json={})
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST /examen/step — submit a reflection, verify phase advances
# ---------------------------------------------------------------------------

async def test_step_advances_to_petition(authed_seeded_client: AsyncClient):
    with patch(
        "app.api.routes.examen._get_ai_response",
        new=AsyncMock(return_value="Dziękuję za tę refleksję."),
    ):
        response = await authed_seeded_client.post(
            f"{BASE}/step",
            json={"session_id": "examen-001", "reflection": "Jestem wdzięczny za zdrowie."},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["phase_completed"] == "gratitude"
    assert data["next_phase"] == "petition"
    assert data["is_final"] is False
    assert DISCLAIMER_FRAGMENT in data["disclaimer"]
    assert "ai_response" in data


async def test_step_returns_404_for_missing_session(authed_client: AsyncClient):
    with patch(
        "app.api.routes.examen._get_ai_response",
        new=AsyncMock(return_value="ok"),
    ):
        response = await authed_client.post(
            f"{BASE}/step",
            json={"session_id": "nonexistent-session", "reflection": "Refleksja"},
        )
    assert response.status_code == 404


async def test_step_empty_reflection_rejected(authed_seeded_client: AsyncClient):
    """Reflection field has min_length=1, empty string must fail validation."""
    response = await authed_seeded_client.post(
        f"{BASE}/step",
        json={"session_id": "examen-001", "reflection": ""},
    )
    assert response.status_code == 422


async def test_step_missing_reflection_rejected(authed_seeded_client: AsyncClient):
    """Missing reflection field altogether."""
    response = await authed_seeded_client.post(
        f"{BASE}/step",
        json={"session_id": "examen-001"},
    )
    assert response.status_code == 422


async def test_step_all_five_phases_exercisable(authed_client: AsyncClient):
    """Start a fresh session and walk through all 5 Ignatian phases."""
    # Start session
    start_resp = await authed_client.post(f"{BASE}/start", json={})
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    with patch(
        "app.api.routes.examen._get_ai_response",
        new=AsyncMock(return_value="Trwaj w ciszy."),
    ):
        completed_phases = []
        for phase in CANONICAL_PHASES:
            resp = await authed_client.post(
                f"{BASE}/step",
                json={"session_id": session_id, "reflection": f"Refleksja dla {phase}."},
            )
            assert resp.status_code == 200, f"Phase {phase} failed: {resp.json()}"
            data = resp.json()
            assert data["phase_completed"] == phase
            completed_phases.append(phase)

        assert completed_phases == CANONICAL_PHASES
        # After the last phase is_final must be True
        assert data["is_final"] is True
        assert data["next_phase"] is None


# ---------------------------------------------------------------------------
# GET /examen/session/{session_id}
# ---------------------------------------------------------------------------

async def test_get_session_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/session/examen-001")
    assert response.status_code == 401


async def test_get_session_returns_state(authed_seeded_client: AsyncClient):
    response = await authed_seeded_client.get(f"{BASE}/session/examen-001")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "examen-001"
    assert data["current_phase"] == "gratitude"
    assert isinstance(data["phases_completed"], list)
    assert "started_at" in data
    assert DISCLAIMER_FRAGMENT in data["disclaimer"]


async def test_get_session_returns_404_for_missing(authed_client: AsyncClient):
    response = await authed_client.get(f"{BASE}/session/does-not-exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /examen/complete
# ---------------------------------------------------------------------------

async def test_complete_requires_auth(app_client: AsyncClient):
    response = await app_client.post(f"{BASE}/complete", json={"session_id": "examen-001"})
    assert response.status_code == 401


async def test_complete_session_without_journal(authed_seeded_client: AsyncClient):
    """Complete without saving to journal — no DB interaction needed."""
    response = await authed_seeded_client.post(
        f"{BASE}/complete",
        json={"session_id": "examen-001", "save_to_journal": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "examen-001"
    assert "summary" in data
    assert data["journal_entry_id"] is None
    assert DISCLAIMER_FRAGMENT in data["disclaimer"]


async def test_complete_session_returns_404_for_missing(authed_client: AsyncClient):
    response = await authed_client.post(
        f"{BASE}/complete",
        json={"session_id": "ghost-session", "save_to_journal": False},
    )
    assert response.status_code == 404


async def test_complete_session_marks_completed_after_all_phases(authed_client: AsyncClient):
    """Start, walk all 5 phases, then complete — verify summary generated."""
    start_resp = await authed_client.post(f"{BASE}/start", json={"intention": "Za pokój"})
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    with patch(
        "app.api.routes.examen._get_ai_response",
        new=AsyncMock(return_value="Bóg jest blisko."),
    ):
        for phase in CANONICAL_PHASES:
            step_resp = await authed_client.post(
                f"{BASE}/step",
                json={"session_id": session_id, "reflection": f"Moje myśli o {phase}."},
            )
            assert step_resp.status_code == 200

    complete_resp = await authed_client.post(
        f"{BASE}/complete",
        json={"session_id": session_id, "save_to_journal": False},
    )
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["journal_entry_id"] is None
    # Summary should contain at least one phase reflection
    assert len(data["summary"]) > 0


# ---------------------------------------------------------------------------
# Mission constraint: disclaimer must always appear
# ---------------------------------------------------------------------------

async def test_disclaimer_in_start_response(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/start", json={})
    data = response.json()
    assert "Asystent refleksji" in data["disclaimer"]
    assert "kapłana" in data["disclaimer"]


async def test_disclaimer_in_step_response(authed_seeded_client: AsyncClient):
    with patch(
        "app.api.routes.examen._get_ai_response",
        new=AsyncMock(return_value="Trwaj w modlitwie."),
    ):
        response = await authed_seeded_client.post(
            f"{BASE}/step",
            json={"session_id": "examen-001", "reflection": "Jestem wdzięczny."},
        )
    data = response.json()
    assert "Asystent refleksji" in data["disclaimer"]


async def test_disclaimer_in_complete_response(authed_seeded_client: AsyncClient):
    response = await authed_seeded_client.post(
        f"{BASE}/complete",
        json={"session_id": "examen-001", "save_to_journal": False},
    )
    data = response.json()
    assert "Asystent refleksji" in data["disclaimer"]
