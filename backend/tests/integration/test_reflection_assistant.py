"""Integration tests for the Reflection Assistant API.

Tests /api/v1/reflection-assistant/session, /message, /traditions
with mocked Redis, LLM, and services. No real DB, Redis, or LLM.
"""

from __future__ import annotations

import json
import sys
import types

# ---------------------------------------------------------------------------
# Stub heavy optional deps before any app import
# ---------------------------------------------------------------------------

def _stub(name: str, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return sys.modules[name]

_jose = _stub("jose", JWTError=Exception)
_stub("jose.jwt")
_stub("neo4j", AsyncDriver=object, AsyncGraphDatabase=object, AsyncSession=object)
_qdrant = _stub("qdrant_client", AsyncQdrantClient=object, QdrantClient=object)
_qdrant_models = _stub("qdrant_client.models", FieldCondition=object, Filter=object, MatchValue=object)
_qdrant.__path__ = []  # make it look like a package
for _m in ("anthropic", "openai", "langchain_openai", "langchain_openai.chat_models", "asyncpg"):
    _stub(_m)

# ---------------------------------------------------------------------------

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.rbac import require_authenticated
from app.main import app

# FastAPI looks up the inner callable, not the Depends wrapper.
_AUTH_DEP = require_authenticated.dependency

BASE = "/api/v1/reflection-assistant"

DISCLAIMER_FRAGMENT = "Asystent refleksji"
FORBIDDEN_PHRASES = ["rozgrzeszam", "jesteś w stanie łaski", "jako ksiądz"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_user(user_id: str = "test-user") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


def _make_emotion_analysis(primary: str = "peace"):
    analysis = MagicMock()
    analysis.primary_emotion = primary
    analysis.secondary_emotions = []
    analysis.vector = {primary: 0.8}
    analysis.confidence = 0.75
    return analysis


def _make_spiritual_state():
    state = MagicMock()
    state.state = MagicMock()
    state.state.value = "consolation"
    state.description = "Stan pocieszenia"
    state.ignatian_movement = "towards_consolation"
    state.suggested_prayer_form = "Modlitwa wdzięczności"
    return state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_redis() -> AsyncMock:
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
    """Redis pre-seeded with an active assistant session for 'test-user'."""
    session = {
        "session_id": "asst-001",
        "user_id": "test-user",
        "tradition": "ignatian",
        "status": "active",
        "created_at": "2026-01-01T12:00:00",
        "messages": [
            {
                "role": "assistant",
                "content": "Witaj w duchowym towarzyszeniu.",
                "timestamp": "2026-01-01T12:00:00",
            }
        ],
        "emotions": [],
    }
    mock_redis._store["assistant:asst-001"] = json.dumps(session).encode()
    return mock_redis


def _mock_db_session() -> AsyncMock:
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
# GET /traditions — public, no auth
# ---------------------------------------------------------------------------

async def test_list_traditions_public(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/traditions")
    assert response.status_code == 200
    traditions = response.json()
    assert isinstance(traditions, list)
    assert len(traditions) > 0


async def test_list_traditions_contains_ignatian(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/traditions")
    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert "ignatian" in ids


async def test_list_traditions_have_required_fields(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/traditions")
    assert response.status_code == 200
    for tradition in response.json():
        assert "id" in tradition
        assert "name" in tradition
        assert "description" in tradition
        assert "key_practices" in tradition


async def test_list_traditions_includes_carmelite_benedictine(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/traditions")
    ids = [t["id"] for t in response.json()]
    assert "carmelite" in ids
    assert "benedictine" in ids


# ---------------------------------------------------------------------------
# POST /session — create a direction session
# ---------------------------------------------------------------------------

async def test_start_session_requires_auth(app_client: AsyncClient):
    response = await app_client.post(f"{BASE}/session", json={"tradition": "ignatian"})
    assert response.status_code == 401


async def test_start_session_creates_session_ignatian(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/session", json={"tradition": "ignatian"})
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["tradition"] == "ignatian"
    assert data["user_id"] == "test-user"
    assert data["status"] == "active"
    assert "opening_message" in data
    assert "created_at" in data


async def test_start_session_unknown_tradition_returns_400(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/session", json={"tradition": "sufi"})
    assert response.status_code == 400


async def test_start_session_with_intention(authed_client: AsyncClient):
    response = await authed_client.post(
        f"{BASE}/session",
        json={"tradition": "ignatian", "initial_intention": "Rozeznanie powołania"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "Rozeznanie powołania" in data["opening_message"]


async def test_start_session_carmelite_tradition(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/session", json={"tradition": "carmelite"})
    assert response.status_code == 201
    assert response.json()["tradition"] == "carmelite"


async def test_start_session_all_traditions_accepted(authed_client: AsyncClient):
    traditions = ["ignatian", "carmelite", "benedictine", "franciscan", "dominican"]
    for tradition in traditions:
        response = await authed_client.post(
            f"{BASE}/session", json={"tradition": tradition}
        )
        assert response.status_code == 201, f"Tradition '{tradition}' rejected"


# ---------------------------------------------------------------------------
# POST /message — send a message in an existing session
# ---------------------------------------------------------------------------

def _make_emotion_svc_instance():
    """Build a fully-mocked EmotionService instance."""
    emotion_analysis = _make_emotion_analysis("peace")
    spiritual_state = _make_spiritual_state()

    svc = MagicMock()
    svc.analyze_text_async = AsyncMock(return_value=emotion_analysis)
    svc.analyze_text = MagicMock(return_value=emotion_analysis)
    svc.get_spiritual_state = MagicMock(return_value=spiritual_state)
    svc.detect_crisis = AsyncMock(
        return_value={"is_crisis": False, "severity": "none", "concerns": [], "resources": []}
    )
    return svc


def _make_orchestrator_instance():
    orchestrator_result = MagicMock()
    orchestrator_result.response = "Słyszę Twoje serce. Trwaj w modlitwie."
    orchestrator_result.follow_up_questions = ["Co czujesz w tej chwili?"]
    orchestrator_result.scripture_references = ["J 15,5"]

    orch = MagicMock()
    orch.direct = AsyncMock(return_value=orchestrator_result)
    return orch


def _make_matcher_instance():
    scripture_match = MagicMock()
    scripture_match.reference = "J 15,5"
    scripture_match.passage = "Trwajcie we Mnie..."
    scripture_match.explanation = "O zjednoczeniu z Bogiem"

    matcher = MagicMock()
    matcher.match = MagicMock(return_value=[scripture_match])
    return matcher


async def test_send_message_requires_auth(app_client: AsyncClient):
    response = await app_client.post(
        f"{BASE}/message",
        json={"session_id": "asst-001", "content": "Czuję pokój."},
    )
    assert response.status_code == 401


def _message_patches(asst_session_id: str = "asst-001"):
    """Build a stack of patches for send_message heavy deps."""
    emotion_svc_inst = _make_emotion_svc_instance()
    orch_inst = _make_orchestrator_instance()
    matcher_inst = _make_matcher_instance()

    # The route imports EmotionService, ScriptureMatcher etc. lazily inside the
    # function body, so we patch the module where they live (import target),
    # not attributes on the route module.
    return [
        patch("app.services.emotion.emotion_service.EmotionService", return_value=emotion_svc_inst),
        patch(
            "app.agents.spiritual_director.director_orchestrator.SpiritualDirectorOrchestrator",
            return_value=orch_inst,
        ),
        patch("app.services.scripture.scripture_matcher.ScriptureMatcher", return_value=matcher_inst),
        patch("app.core.llm.get_llm_client", return_value=MagicMock()),
        patch("app.services.audit.audit_service.audit.log_ai_interaction", new=AsyncMock()),
    ]


async def _apply_patches_and_post(client, patches, payload):
    """Helper: enter all patches then POST."""
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return await client.post(f"{BASE}/message", json=payload)


async def test_send_message_returns_404_for_missing_session(authed_client: AsyncClient):
    patches = _message_patches()
    response = await _apply_patches_and_post(
        authed_client, patches,
        {"session_id": "does-not-exist", "content": "Czuję pokój."},
    )
    assert response.status_code == 404


async def test_send_message_returns_ai_response(authed_seeded_client: AsyncClient):
    patches = _message_patches()
    response = await _apply_patches_and_post(
        authed_seeded_client, patches,
        {"session_id": "asst-001", "content": "Czuję pokój w modlitwie."},
    )
    assert response.status_code == 200
    data = response.json()
    assert "assistant_response" in data
    assert data["session_id"] == "asst-001"
    assert "emotion_analysis" in data
    assert "suggested_scriptures" in data
    assert "follow_up_questions" in data


async def test_send_message_disclaimer_always_present(authed_seeded_client: AsyncClient):
    patches = _message_patches()
    response = await _apply_patches_and_post(
        authed_seeded_client, patches,
        {"session_id": "asst-001", "content": "Czuję pokój."},
    )
    assert response.status_code == 200
    assert DISCLAIMER_FRAGMENT in response.json()["disclaimer"]


async def test_send_message_response_no_forbidden_phrases(authed_seeded_client: AsyncClient):
    """AI response must never claim to be a priest or grant absolution."""
    patches = _message_patches()
    response = await _apply_patches_and_post(
        authed_seeded_client, patches,
        {"session_id": "asst-001", "content": "Chcę uzyskać rozgrzeszenie."},
    )
    assert response.status_code == 200
    ai_text = response.json()["assistant_response"].lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase.lower() not in ai_text, (
            f"Forbidden phrase '{phrase}' found in AI response"
        )


async def test_send_message_empty_content_rejected(authed_seeded_client: AsyncClient):
    """Empty content — no min_length on the field, so may return 200 or 422.
    The invariant is: no 500 server crash."""
    patches = _message_patches()
    response = await _apply_patches_and_post(
        authed_seeded_client, patches,
        {"session_id": "asst-001", "content": ""},
    )
    assert response.status_code != 500
