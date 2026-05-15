"""Integration tests for Lectio Divina API routes.

Tests /run, /journey/me, /patterns/me, /history/me,
/session, /emotion, /reflection with mocked Redis and LLM calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.rbac import require_authenticated
from app.main import app


BASE = "/api/v1/lectio-divina"


def _mock_user(user_id: str = "test-user") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


@pytest_asyncio.fixture()
async def authed_client(app_client: AsyncClient):
    """app_client with require_authenticated overridden to return 'test-user'."""
    app.dependency_overrides[require_authenticated] = lambda: _mock_user()
    yield app_client
    app.dependency_overrides.pop(require_authenticated, None)


@pytest_asyncio.fixture()
async def authed_seeded_client(seeded_client: AsyncClient):
    """seeded_client with require_authenticated overridden to return 'test-user'."""
    app.dependency_overrides[require_authenticated] = lambda: _mock_user()
    yield seeded_client
    app.dependency_overrides.pop(require_authenticated, None)


# ---------------------------------------------------------------------------
# GET /scripture/{date}  — public, no auth required
# ---------------------------------------------------------------------------

async def test_get_scripture_for_date(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/scripture/2026-01-01")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "season" in data
    assert "readings" in data


async def test_get_scripture_invalid_date(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/scripture/not-a-date")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /session
# ---------------------------------------------------------------------------

async def test_start_session_requires_auth(app_client: AsyncClient):
    response = await app_client.post(f"{BASE}/session", json={"tradition": "ignatian"})
    assert response.status_code == 401


async def test_start_session_creates_session(authed_client: AsyncClient):
    response = await authed_client.post(f"{BASE}/session", json={"tradition": "ignatian"})
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["user_id"] == "test-user"
    assert data["stage"] == "lectio"


# ---------------------------------------------------------------------------
# POST /emotion
# ---------------------------------------------------------------------------

async def test_analyze_emotion_requires_text_or_audio(authed_seeded_client: AsyncClient):
    """No text and no audio_url → 400."""
    response = await authed_seeded_client.post(
        f"{BASE}/emotion",
        json={"session_id": "sess-001"},
    )
    assert response.status_code == 400


async def test_analyze_emotion_with_text(authed_seeded_client: AsyncClient):
    emotion_result = MagicMock()
    emotion_result.primary_emotion = "peace"
    emotion_result.secondary_emotions = []
    emotion_result.vector = {"peace": 0.9}
    emotion_result.confidence = 0.85
    emotion_result.spiritual_state = MagicMock(value="consolation")

    with patch("app.services.emotion.emotion_service.EmotionService.analyze_text", return_value=emotion_result):
        with patch("app.services.scripture.scripture_matcher.ScriptureMatcher.match", return_value=[]):
            response = await authed_seeded_client.post(
                f"{BASE}/emotion",
                json={
                    "session_id": "sess-001",
                    "text": "Czuję spokój i wdzięczność w modlitwie.",
                },
            )
    assert response.status_code == 200
    data = response.json()
    assert "primary_emotion" in data
    assert "confidence" in data
    assert "spiritual_state" in data


# ---------------------------------------------------------------------------
# POST /reflection
# ---------------------------------------------------------------------------

async def test_submit_reflection_advances_stage(authed_seeded_client: AsyncClient):
    response = await authed_seeded_client.post(
        f"{BASE}/reflection",
        json={
            "session_id": "sess-001",
            "stage": "lectio",
            "reflection_text": "Słowo 'trwaj' dotknęło moje serce.",
            "grace_notes": ["cisza", "obecność"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["next_stage"] == "meditatio"


async def test_submit_reflection_invalid_stage(authed_seeded_client: AsyncClient):
    response = await authed_seeded_client.post(
        f"{BASE}/reflection",
        json={
            "session_id": "sess-001",
            "stage": "invalid_stage",
            "reflection_text": "test",
        },
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /history/me
# ---------------------------------------------------------------------------

async def test_get_history_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/history/me")
    assert response.status_code == 401


async def test_get_history_returns_list(authed_seeded_client: AsyncClient):
    response = await authed_seeded_client.get(f"{BASE}/history/me")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# POST /run — full pipeline (mocked LLM)
# ---------------------------------------------------------------------------

async def test_run_pipeline_requires_auth(app_client: AsyncClient):
    response = await app_client.post(f"{BASE}/run", json={"emotion_text": "Czuję spokój."})
    assert response.status_code == 401


async def test_run_pipeline_returns_expected_shape(authed_client: AsyncClient):
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
            response = await authed_client.post(
                f"{BASE}/run",
                json={"emotion_text": "Czuję spokój.", "tradition": "ignatian"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "scripture" in data
    assert "prayer" in data
    assert "tradition" in data
    assert "kerygmatic_theme" in data
    assert "journey" in data


# ---------------------------------------------------------------------------
# GET /journey/me
# ---------------------------------------------------------------------------

async def test_get_journey_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/journey/me")
    assert response.status_code == 401


async def test_get_journey_returns_stage_info(authed_seeded_client: AsyncClient):
    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        inst = MockLLM.return_value
        inst.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="STAGE: illumination\nPROGRESS: 55\nMILESTONE: Głębsza modlitwa\nGROWTH: Kontemplacja"
            )
        )
        response = await authed_seeded_client.get(f"{BASE}/journey/me")

    assert response.status_code == 200
    data = response.json()
    assert "current_stage" in data
    assert "progress_percentage" in data


async def test_get_journey_is_cached_on_second_call(authed_seeded_client: AsyncClient):
    """Second call should hit Redis cache, not the LLM."""
    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        inst = MockLLM.return_value
        inst.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="STAGE: purgation\nPROGRESS: 20\nMILESTONE: -\nGROWTH: Modlitwa"
            )
        )
        r1 = await authed_seeded_client.get(f"{BASE}/journey/me")
        first_call_count = inst.ainvoke.call_count

        r2 = await authed_seeded_client.get(f"{BASE}/journey/me")
        second_call_count = inst.ainvoke.call_count

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert second_call_count == first_call_count


# ---------------------------------------------------------------------------
# GET /patterns/me
# ---------------------------------------------------------------------------

async def test_get_patterns_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f"{BASE}/patterns/me")
    assert response.status_code == 401


async def test_get_patterns_returns_list(authed_seeded_client: AsyncClient):
    with patch("app.agents.memory.pattern_discovery.ChatOpenAI") as MockLLM:
        inst = MockLLM.return_value
        inst.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="PATTERN: recurring_theme\nDESC: Zaufanie\nFREQ: tygodniowo\nSCRIPTURE: Ps 23"
            )
        )
        response = await authed_seeded_client.get(f"{BASE}/patterns/me")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
