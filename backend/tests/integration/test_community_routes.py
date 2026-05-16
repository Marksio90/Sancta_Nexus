"""Integration tests for Community API routes.

Tests /api/v1/community/intentions and /groups endpoints
with mocked DB services. No real DB, Redis, or LLM.
"""

from __future__ import annotations

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

BASE = "/api/v1/community"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_user(user_id: str = "test-user") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


def _mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.set = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    redis.delete = AsyncMock()
    return redis


def _intention_dict(
    idx: int = 1,
    status: str = "PENDING_MODERATION",
    prayer_count: int = 0,
) -> dict:
    return {
        "id": f"intention-{idx}",
        "content": f"Prośba modlitewna {idx}",
        "is_public": True,
        "category": "general",
        "author_display": "Anonim",
        "prayer_count": prayer_count,
        "status": status,
        "user_id": None,
        "group_id": None,
        "created_at": "2026-01-01T10:00:00",
        "expires_at": "2026-02-01T10:00:00",
    }


def _group_dict(idx: int = 1) -> dict:
    return {
        "id": f"group-{idx}",
        "name": f"Wspólnota {idx}",
        "description": "Opis wspólnoty",
        "category": "różaniec",
        "schedule": "Niedziela 18:00",
        "parish": "Parafia Testowa",
        "leader_user_id": "test-user",
        "member_count": 5,
        "created_at": "2026-01-01T10:00:00",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_db_session() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest_asyncio.fixture()
async def app_client():
    from app.core.dependencies import get_db, get_redis_client
    redis = _mock_redis()
    mock_db = _mock_db_session()
    app.dependency_overrides[get_redis_client] = lambda: redis
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def authed_client(app_client: AsyncClient):
    app.dependency_overrides[_AUTH_DEP] = lambda: _mock_user()
    yield app_client
    app.dependency_overrides.pop(_AUTH_DEP, None)


# ---------------------------------------------------------------------------
# GET /intentions — public, no auth required
# ---------------------------------------------------------------------------

async def test_list_intentions_public_unauthenticated(app_client: AsyncClient):
    intention_svc = AsyncMock()
    intention_svc.list_public = AsyncMock(return_value=[_intention_dict(1), _intention_dict(2)])

    with patch(
        "app.api.routes.community._intentions",
        return_value=intention_svc,
    ):
        response = await app_client.get(f"{BASE}/intentions")

    assert response.status_code == 200
    data = response.json()
    assert "intentions" in data
    assert len(data["intentions"]) == 2


async def test_list_intentions_returns_categories(app_client: AsyncClient):
    intention_svc = AsyncMock()
    intention_svc.list_public = AsyncMock(return_value=[])

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.get(f"{BASE}/intentions")

    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0


async def test_list_intentions_with_category_filter(app_client: AsyncClient):
    intention_svc = AsyncMock()
    intention_svc.list_public = AsyncMock(return_value=[])

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.get(f"{BASE}/intentions?category=zdrowie")

    assert response.status_code == 200
    # Verify service was called with category filter
    intention_svc.list_public.assert_awaited_once()
    call_kwargs = intention_svc.list_public.call_args
    assert call_kwargs.kwargs.get("category") == "zdrowie"


async def test_list_intentions_pagination_params(app_client: AsyncClient):
    intention_svc = AsyncMock()
    intention_svc.list_public = AsyncMock(return_value=[])

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.get(f"{BASE}/intentions?limit=10&offset=20")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /intentions — create intention (auth optional by route, but test both)
# ---------------------------------------------------------------------------

async def test_create_intention_unauthenticated_allowed(app_client: AsyncClient):
    """Route uses get_optional_user — anonymous submissions are allowed."""
    created = _intention_dict(1, status="PENDING_MODERATION")
    intention_svc = AsyncMock()
    intention_svc.create = AsyncMock(return_value=created)

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.post(
            f"{BASE}/intentions",
            json={"content": "Proszę o modlitwę za zdrowie.", "is_public": True},
        )

    assert response.status_code == 201
    data = response.json()
    assert "status" in data
    assert data["status"] == "PENDING_MODERATION"


async def test_create_intention_authenticated(authed_client: AsyncClient):
    created = _intention_dict(2, status="PENDING_MODERATION")
    intention_svc = AsyncMock()
    intention_svc.create = AsyncMock(return_value=created)

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await authed_client.post(
            f"{BASE}/intentions",
            json={"content": "Modlitwa za rodzinę.", "is_public": True, "category": "rodzina"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "status" in data


async def test_create_intention_missing_content_rejected(app_client: AsyncClient):
    """content field has min_length=5, missing it must return 422."""
    response = await app_client.post(
        f"{BASE}/intentions",
        json={"is_public": True},
    )
    assert response.status_code == 422


async def test_create_intention_too_short_content_rejected(app_client: AsyncClient):
    """Content shorter than min_length=5 must return 422."""
    response = await app_client.post(
        f"{BASE}/intentions",
        json={"content": "ok", "is_public": True},
    )
    assert response.status_code == 422


async def test_private_intention_status(app_client: AsyncClient):
    """Private intentions skip moderation and become ACTIVE immediately."""
    created = _intention_dict(3, status="ACTIVE")
    intention_svc = AsyncMock()
    intention_svc.create = AsyncMock(return_value=created)

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.post(
            f"{BASE}/intentions",
            json={"content": "Prywatna intencja.", "is_public": False},
        )

    assert response.status_code == 201
    # The service mock returns ACTIVE — verify field is present
    assert response.json()["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# POST /intentions/{id}/pray — increment prayer count (public)
# ---------------------------------------------------------------------------

async def test_pray_for_intention_increments_count(app_client: AsyncClient):
    updated = _intention_dict(1, prayer_count=1)
    intention_svc = AsyncMock()
    intention_svc.intercede = AsyncMock(return_value=updated)

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.post(f"{BASE}/intentions/intention-1/pray")

    assert response.status_code == 200
    data = response.json()
    assert data["prayer_count"] == 1


async def test_pray_for_nonexistent_intention_returns_404(app_client: AsyncClient):
    intention_svc = AsyncMock()
    intention_svc.intercede = AsyncMock(return_value=None)

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.post(f"{BASE}/intentions/ghost-id/pray")

    assert response.status_code == 404


async def test_pray_for_intention_no_auth_needed(app_client: AsyncClient):
    """Prayer count endpoint is public — no authentication required."""
    intention_svc = AsyncMock()
    intention_svc.intercede = AsyncMock(return_value=_intention_dict(1, prayer_count=5))

    with patch("app.api.routes.community._intentions", return_value=intention_svc):
        response = await app_client.post(f"{BASE}/intentions/intention-1/pray")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /groups — public
# ---------------------------------------------------------------------------

async def test_list_groups_unauthenticated(app_client: AsyncClient):
    group_svc = AsyncMock()
    group_svc.list_groups = AsyncMock(return_value=[_group_dict(1), _group_dict(2)])

    with patch("app.api.routes.community._groups", return_value=group_svc):
        response = await app_client.get(f"{BASE}/groups")

    assert response.status_code == 200
    data = response.json()
    assert "groups" in data
    assert len(data["groups"]) == 2


async def test_list_groups_returns_categories(app_client: AsyncClient):
    group_svc = AsyncMock()
    group_svc.list_groups = AsyncMock(return_value=[])

    with patch("app.api.routes.community._groups", return_value=group_svc):
        response = await app_client.get(f"{BASE}/groups")

    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)


async def test_list_groups_with_category_filter(app_client: AsyncClient):
    group_svc = AsyncMock()
    group_svc.list_groups = AsyncMock(return_value=[])

    with patch("app.api.routes.community._groups", return_value=group_svc):
        response = await app_client.get(f"{BASE}/groups?category=różaniec")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /groups — create group (auth required)
# ---------------------------------------------------------------------------

async def test_create_group_requires_auth(app_client: AsyncClient):
    response = await app_client.post(
        f"{BASE}/groups",
        json={"name": "Nowa Wspólnota", "category": "ogólna"},
    )
    assert response.status_code == 401


async def test_create_group_authenticated(authed_client: AsyncClient):
    created = _group_dict(1)
    group_svc = AsyncMock()
    group_svc.create_group = AsyncMock(return_value=created)

    with patch("app.api.routes.community._groups", return_value=group_svc):
        response = await authed_client.post(
            f"{BASE}/groups",
            json={
                "name": "Wspólnota Młodych",
                "description": "Modlitwa dla młodzieży",
                "category": "młodzież",
                "schedule": "Piątek 19:00",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "name" in data


async def test_create_group_name_too_short_rejected(authed_client: AsyncClient):
    """name has min_length=3."""
    response = await authed_client.post(
        f"{BASE}/groups",
        json={"name": "AB", "category": "ogólna"},
    )
    assert response.status_code == 422


async def test_create_group_missing_name_rejected(authed_client: AsyncClient):
    response = await authed_client.post(
        f"{BASE}/groups",
        json={"category": "ogólna"},
    )
    assert response.status_code == 422


async def test_create_group_with_parish(authed_client: AsyncClient):
    created = _group_dict(2)
    group_svc = AsyncMock()
    group_svc.create_group = AsyncMock(return_value=created)

    with patch("app.api.routes.community._groups", return_value=group_svc):
        response = await authed_client.post(
            f"{BASE}/groups",
            json={
                "name": "Różaniec Parafialny",
                "category": "różaniec",
                "parish": "Parafia Wniebowzięcia NMP",
            },
        )

    assert response.status_code == 201
    # Verify service received parish param
    group_svc.create_group.assert_awaited_once()
    call_kwargs = group_svc.create_group.call_args.kwargs
    assert call_kwargs.get("parish") == "Parafia Wniebowzięcia NMP"
    assert call_kwargs.get("leader_user_id") == "test-user"
