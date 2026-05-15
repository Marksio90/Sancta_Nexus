"""Integration tests for the OrchestratorSupremus (A-001) API route.

Tests POST /api/v1/orchestrate with mocked LangGraph execution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.rbac import require_authenticated
from app.main import app


ORCHESTRATE_URL = "/api/v1/orchestrate"


def _mock_user(user_id: str = "test-user") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = "user"
    return user


async def test_orchestrate_returns_expected_shape(app_client: AsyncClient):
    """Minimal payload — orchestrator should return valid JSON with intent + content."""
    mock_state = {
        "intent": "lectio_divina",
        "scripture": {"book": "J", "chapter": 15, "text": "..."},
        "prayer": {"prayer_text": "Amen.", "tradition": "ignatian"},
        "error": None,
    }

    app.dependency_overrides[require_authenticated] = lambda: _mock_user()

    try:
        with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
            inst = MockOrch.return_value
            inst.run = AsyncMock(return_value=mock_state)

            response = await app_client.post(
                ORCHESTRATE_URL,
                json={"emotion_vector": {"peace": 0.8, "gratitude": 0.5}},
            )
    finally:
        app.dependency_overrides.pop(require_authenticated, None)

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "lectio_divina"
    assert "scripture" in data
    assert "prayer" in data
    assert data["error"] is None


async def test_orchestrate_explicit_intent_skips_routing(app_client: AsyncClient):
    """When intent is explicitly provided, the orchestrator receives it pre-set."""
    mock_state = {
        "intent": "crisis",
        "prayer": {"text": "Jesteś ważny.", "tradition": "universal"},
        "action": {"challenge": "Zadzwoń: 116 123"},
        "error": None,
    }

    app.dependency_overrides[require_authenticated] = lambda: _mock_user()

    try:
        with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
            inst = MockOrch.return_value
            inst.run = AsyncMock(return_value=mock_state)

            response = await app_client.post(
                ORCHESTRATE_URL,
                json={"intent": "crisis"},
            )
    finally:
        app.dependency_overrides.pop(require_authenticated, None)

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "crisis"

    # Check that intent was forwarded to orchestrator
    call_args = inst.run.call_args
    initial_state = call_args.args[0] if call_args.args else call_args.kwargs.get("state", {})
    assert initial_state.get("intent") == "crisis"


async def test_orchestrate_500_on_pipeline_failure(app_client: AsyncClient):
    """If OrchestratorSupremus.run raises, route must return 500."""
    app.dependency_overrides[require_authenticated] = lambda: _mock_user()

    try:
        with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
            inst = MockOrch.return_value
            inst.run = AsyncMock(side_effect=RuntimeError("LangGraph internal error"))

            response = await app_client.post(ORCHESTRATE_URL, json={})
    finally:
        app.dependency_overrides.pop(require_authenticated, None)

    assert response.status_code == 500
    assert "Orchestration pipeline failed" in response.json()["detail"]


async def test_orchestrate_requires_auth(app_client: AsyncClient):
    """Unauthenticated request must be rejected with 401."""
    response = await app_client.post(ORCHESTRATE_URL, json={})
    assert response.status_code == 401


async def test_orchestrate_user_id_sourced_from_jwt(app_client: AsyncClient):
    """user_id in orchestrator initial_state must come from JWT, not request body."""
    captured: list[dict] = []
    mock_state = {"intent": "free_reflection", "error": None}

    app.dependency_overrides[require_authenticated] = lambda: _mock_user("jwt-user-id")

    try:
        with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
            inst = MockOrch.return_value

            async def _capture_run(state: dict) -> dict:
                captured.append(state)
                return mock_state

            inst.run.side_effect = _capture_run

            await app_client.post(ORCHESTRATE_URL, json={"intent": "free_reflection"})
    finally:
        app.dependency_overrides.pop(require_authenticated, None)

    assert len(captured) == 1
    assert captured[0]["user_id"] == "jwt-user-id"


async def test_orchestrate_health_check(app_client: AsyncClient):
    """The /health endpoint should always return 200."""
    response = await app_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
