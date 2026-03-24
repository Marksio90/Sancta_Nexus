"""Integration tests for the OrchestratorSupremus (A-001) API route.

Tests POST /api/v1/orchestrate with mocked LangGraph execution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


ORCHESTRATE_URL = "/api/v1/orchestrate"


async def test_orchestrate_returns_expected_shape(app_client: AsyncClient):
    """Minimal payload — orchestrator should return valid JSON with intent + content."""
    mock_state = {
        "user_id": "test-user",
        "intent": "lectio_divina",
        "scripture": {"book": "J", "chapter": 15, "text": "..."},
        "prayer": {"prayer_text": "Amen.", "tradition": "ignatian"},
        "error": None,
    }

    with patch(
        "app.api.routes.orchestrate.OrchestratorSupremus"
    ) as MockOrch:
        inst = MockOrch.return_value
        inst.run = AsyncMock(return_value=mock_state)

        response = await app_client.post(
            ORCHESTRATE_URL,
            json={
                "user_id": "test-user",
                "emotion_vector": {"peace": 0.8, "gratitude": 0.5},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user"
    assert data["intent"] == "lectio_divina"
    assert "scripture" in data
    assert "prayer" in data
    assert data["error"] is None


async def test_orchestrate_explicit_intent_skips_routing(app_client: AsyncClient):
    """When intent is explicitly provided, the orchestrator receives it pre-set."""
    mock_state = {
        "user_id": "test-user",
        "intent": "crisis",
        "prayer": {"text": "Jesteś ważny.", "tradition": "universal"},
        "action": {"challenge": "Zadzwoń: 116 123"},
        "error": None,
    }

    with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
        inst = MockOrch.return_value
        inst.run = AsyncMock(return_value=mock_state)

        response = await app_client.post(
            ORCHESTRATE_URL,
            json={"user_id": "test-user", "intent": "crisis"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "crisis"

    # Check that intent was forwarded to orchestrator
    call_args = inst.run.call_args
    initial_state = call_args.args[0] if call_args.args else call_args.kwargs.get("state", {})
    assert initial_state.get("intent") == "crisis"


async def test_orchestrate_500_on_pipeline_failure(app_client: AsyncClient):
    """If OrchestratorSupremus.run raises, route must return 500."""
    with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
        inst = MockOrch.return_value
        inst.run = AsyncMock(side_effect=RuntimeError("LangGraph internal error"))

        response = await app_client.post(
            ORCHESTRATE_URL,
            json={"user_id": "test-user"},
        )

    assert response.status_code == 500
    assert "Orchestration pipeline failed" in response.json()["detail"]


async def test_orchestrate_anonymous_user_allowed(app_client: AsyncClient):
    """Default user_id 'anonymous' must work without errors."""
    mock_state = {"user_id": "anonymous", "intent": "free_reflection", "error": None}

    with patch("app.api.routes.orchestrate.OrchestratorSupremus") as MockOrch:
        inst = MockOrch.return_value
        inst.run = AsyncMock(return_value=mock_state)

        response = await app_client.post(ORCHESTRATE_URL, json={})

    assert response.status_code == 200
    assert response.json()["user_id"] == "anonymous"


async def test_orchestrate_health_check(app_client: AsyncClient):
    """The /health endpoint should always return 200."""
    response = await app_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
