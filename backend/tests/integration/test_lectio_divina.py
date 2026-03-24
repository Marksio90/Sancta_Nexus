"""Integration tests for Lectio Divina API routes.

Tests /run, /journey/{user_id}, /patterns/{user_id}, /history/{user_id},
/session, /emotion, /reflection with mocked Redis and LLM calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/v1/lectio-divina/scripture/{date}
# ---------------------------------------------------------------------------

async def test_get_scripture_for_date(app_client: AsyncClient):
    response = await app_client.get("/api/v1/lectio-divina/scripture/2026-01-01")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "season" in data
    assert "readings" in data


async def test_get_scripture_invalid_date(app_client: AsyncClient):
    response = await app_client.get("/api/v1/lectio-divina/scripture/not-a-date")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/lectio-divina/session
# ---------------------------------------------------------------------------

async def test_start_session_creates_session(app_client: AsyncClient):
    response = await app_client.post(
        "/api/v1/lectio-divina/session",
        json={"user_id": "test-user", "tradition": "ignatian"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["user_id"] == "test-user"
    assert data["stage"] == "lectio"


# ---------------------------------------------------------------------------
# POST /api/v1/lectio-divina/emotion
# ---------------------------------------------------------------------------

async def test_analyze_emotion_requires_text_or_audio(seeded_client: AsyncClient):
    response = await seeded_client.post(
        "/api/v1/lectio-divina/emotion",
        json={"session_id": "sess-001", "user_id": "test-user"},
    )
    assert response.status_code == 400


async def test_analyze_emotion_with_text(seeded_client: AsyncClient):
    response = await seeded_client.post(
        "/api/v1/lectio-divina/emotion",
        json={
            "session_id": "sess-001",
            "user_id": "test-user",
            "text": "Czuję spokój i wdzięczność w modlitwie.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "primary_emotion" in data
    assert "confidence" in data
    assert "spiritual_state" in data


# ---------------------------------------------------------------------------
# POST /api/v1/lectio-divina/reflection
# ---------------------------------------------------------------------------

async def test_submit_reflection_advances_stage(seeded_client: AsyncClient):
    response = await seeded_client.post(
        "/api/v1/lectio-divina/reflection",
        json={
            "session_id": "sess-001",
            "user_id": "test-user",
            "stage": "lectio",
            "reflection_text": "Słowo 'trwaj' dotknęło moje serce.",
            "grace_notes": ["cisza", "obecność"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["next_stage"] == "meditatio"


async def test_submit_reflection_invalid_stage(seeded_client: AsyncClient):
    response = await seeded_client.post(
        "/api/v1/lectio-divina/reflection",
        json={
            "session_id": "sess-001",
            "user_id": "test-user",
            "stage": "invalid_stage",
            "reflection_text": "test",
        },
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/v1/lectio-divina/history/{user_id}
# ---------------------------------------------------------------------------

async def test_get_history_returns_list(seeded_client: AsyncClient):
    response = await seeded_client.get("/api/v1/lectio-divina/history/test-user")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# POST /api/v1/lectio-divina/run — full pipeline (mocked LLM)
# ---------------------------------------------------------------------------

async def test_run_pipeline_returns_expected_shape(app_client: AsyncClient):
    mock_session_result = {
        "scripture": {"book": "J", "chapter": 15, "verse_start": 5, "verse_end": 5, "text": "..."},
        "meditation": {"questions": [], "reflection_layers": {}, "key_word": "trwaj"},
        "prayer": {"prayer_text": "Amen.", "tradition": "ignatian", "elements": [], "spiritual_movement": "peace"},
        "contemplation": {"guidance_text": "...", "sacred_word": "Trwaj"},
        "action": {"challenge_text": "...", "difficulty": "easy"},
        "tradition": "ignatian",
        "kerygmatic_theme": "mysterium_paschale",
        "error": None,
    }

    with patch("app.api.routes.lectio_divina.run_session", return_value=mock_session_result):
        with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
            inst = MockLLM.return_value
            inst.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="STAGE: purgation\nPROGRESS: 10\nMILESTONE: Start\nGROWTH: Modlitwa"
                )
            )

            response = await app_client.post(
                "/api/v1/lectio-divina/run",
                json={"emotion_text": "Czuję spokój.", "user_id": "test-user", "tradition": "ignatian"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "scripture" in data
    assert "prayer" in data
    assert "tradition" in data
    assert "kerygmatic_theme" in data
    # journey field should be present (may be None if tracker fails gracefully)
    assert "journey" in data


# ---------------------------------------------------------------------------
# GET /api/v1/lectio-divina/journey/{user_id}
# ---------------------------------------------------------------------------

async def test_get_journey_returns_stage_info(seeded_client: AsyncClient):
    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        inst = MockLLM.return_value
        inst.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="STAGE: illumination\nPROGRESS: 55\nMILESTONE: Głębsza modlitwa\nGROWTH: Kontemplacja"
            )
        )
        response = await seeded_client.get("/api/v1/lectio-divina/journey/test-user")

    assert response.status_code == 200
    data = response.json()
    assert "current_stage" in data
    assert "progress_percentage" in data


async def test_get_journey_is_cached_on_second_call(seeded_client: AsyncClient):
    """Second call should hit Redis cache, not the LLM."""
    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        inst = MockLLM.return_value
        inst.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="STAGE: purgation\nPROGRESS: 20\nMILESTONE: -\nGROWTH: Modlitwa"
            )
        )
        # First call — hits LLM
        r1 = await seeded_client.get("/api/v1/lectio-divina/journey/test-user")
        first_call_count = inst.ainvoke.call_count

        # Second call — should use Redis cache
        r2 = await seeded_client.get("/api/v1/lectio-divina/journey/test-user")
        second_call_count = inst.ainvoke.call_count

    assert r1.status_code == 200
    assert r2.status_code == 200
    # LLM not called again on second request
    assert second_call_count == first_call_count


# ---------------------------------------------------------------------------
# GET /api/v1/lectio-divina/patterns/{user_id}
# ---------------------------------------------------------------------------

async def test_get_patterns_returns_list(seeded_client: AsyncClient):
    with patch("app.agents.memory.pattern_discovery.ChatOpenAI") as MockLLM:
        inst = MockLLM.return_value
        inst.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="PATTERN: recurring_theme\nDESC: Zaufanie\nFREQ: tygodniowo\nSCRIPTURE: Ps 23"
            )
        )
        response = await seeded_client.get("/api/v1/lectio-divina/patterns/test-user")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
