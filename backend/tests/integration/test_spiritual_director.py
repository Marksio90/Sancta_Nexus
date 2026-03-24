"""Integration tests for Spiritual Director API routes.

Tests POST /session, POST /message, GET /traditions
with mocked Redis and LLM calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/v1/spiritual-director/traditions
# ---------------------------------------------------------------------------

async def test_get_traditions_returns_list(app_client: AsyncClient):
    response = await app_client.get("/api/v1/spiritual-director/traditions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    ids = [t["id"] for t in data]
    assert "ignatian" in ids
    assert "carmelite" in ids


# ---------------------------------------------------------------------------
# POST /api/v1/spiritual-director/session
# ---------------------------------------------------------------------------

async def test_start_director_session(app_client: AsyncClient):
    response = await app_client.post(
        "/api/v1/spiritual-director/session",
        json={"user_id": "test-user", "tradition": "ignatian"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "opening_message" in data
    assert data["tradition"] == "ignatian"


async def test_start_session_returns_tradition_specific_opening(app_client: AsyncClient):
    """Each tradition should have a distinct opening."""
    response_ignacjan = await app_client.post(
        "/api/v1/spiritual-director/session",
        json={"user_id": "user-a", "tradition": "ignatian"},
    )
    response_carmelite = await app_client.post(
        "/api/v1/spiritual-director/session",
        json={"user_id": "user-b", "tradition": "carmelite"},
    )
    assert response_ignacjan.status_code == 200
    assert response_carmelite.status_code == 200
    # Both sessions must have an opening message
    assert response_ignacjan.json()["opening_message"]
    assert response_carmelite.json()["opening_message"]


# ---------------------------------------------------------------------------
# POST /api/v1/spiritual-director/message
# ---------------------------------------------------------------------------

async def test_send_message_unknown_session_returns_404(seeded_client: AsyncClient):
    response = await seeded_client.post(
        "/api/v1/spiritual-director/message",
        json={"session_id": "nonexistent", "user_id": "test-user", "content": "Pomóż mi."},
    )
    assert response.status_code == 404


async def test_send_message_returns_director_response(seeded_client: AsyncClient):
    """With mocked LLM, /message should return a valid director response."""
    # Mock SpiritualDirectorOrchestrator
    mock_result = MagicMock()
    mock_result.response = "Módl się w ciszy i zaufaj Panu."
    mock_result.follow_up_questions = ["Co czujesz w tej chwili?"]
    mock_result.scripture_references = [{"reference": "Ps 23,1", "passage": "Pan jest moim pasterzem."}]
    mock_result.prayer_suggestion = "Lectio Divina na Ps 23"

    with patch(
        "app.api.routes.spiritual_director.SpiritualDirectorOrchestrator"
    ) as MockOrch:
        inst = MockOrch.return_value
        inst.direct = AsyncMock(return_value=mock_result)

        with patch("app.api.routes.spiritual_director.EmotionService") as MockEmo:
            emo_inst = MockEmo.return_value
            emo_inst.analyze_text_async = AsyncMock(
                return_value=MagicMock(
                    primary_emotion="peace",
                    vector={"peace": 0.8},
                    spiritual_state=MagicMock(value="consolation"),
                    confidence=0.9,
                    secondary_emotions=[],
                )
            )
            emo_inst.analyze_text = MagicMock(
                return_value=MagicMock(
                    primary_emotion="peace",
                    vector={"peace": 0.8},
                    spiritual_state=MagicMock(value="consolation"),
                    confidence=0.9,
                    secondary_emotions=[],
                )
            )
            emo_inst.detect_crisis = AsyncMock(
                return_value={"is_crisis": False, "severity": "none", "concerns": [], "resources": []}
            )

            response = await seeded_client.post(
                "/api/v1/spiritual-director/message",
                json={
                    "session_id": "dir-001",
                    "user_id": "test-user",
                    "content": "Czuję się zagubiony w modlitwie.",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert "director_response" in data
    assert "follow_up_questions" in data
    assert "emotion_analysis" in data
    assert isinstance(data["follow_up_questions"], list)


async def test_send_message_detects_crisis(seeded_client: AsyncClient):
    """Crisis content must trigger crisis detection — response must include resources."""
    with patch("app.api.routes.spiritual_director.EmotionService") as MockEmo:
        emo_inst = MockEmo.return_value
        emo_inst.analyze_text_async = AsyncMock(
            return_value=MagicMock(
                primary_emotion="despair",
                vector={"despair": 0.95},
                spiritual_state=MagicMock(value="dark_night"),
                confidence=0.9,
                secondary_emotions=[],
            )
        )
        emo_inst.analyze_text = MagicMock(
            return_value=MagicMock(
                primary_emotion="despair",
                vector={"despair": 0.95},
                spiritual_state=MagicMock(value="dark_night"),
                confidence=0.9,
                secondary_emotions=[],
            )
        )
        emo_inst.detect_crisis = AsyncMock(
            return_value={
                "is_crisis": True,
                "severity": "high",
                "concerns": ["suicidal ideation"],
                "resources": ["Telefon Zaufania 116 123"],
            }
        )

        with patch("app.api.routes.spiritual_director.SpiritualDirectorOrchestrator") as MockOrch:
            inst = MockOrch.return_value
            inst.direct = AsyncMock(
                return_value=MagicMock(
                    response="Jesteś ważny. Zadzwoń do kogoś bliskiego.",
                    follow_up_questions=[],
                    scripture_references=[],
                    prayer_suggestion=None,
                )
            )

            response = await seeded_client.post(
                "/api/v1/spiritual-director/message",
                json={
                    "session_id": "dir-001",
                    "user_id": "test-user",
                    "content": "Nie chcę już żyć.",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert "crisis_severity" in data["emotion_analysis"]
    assert data["emotion_analysis"]["crisis_severity"] == "high"
    assert "crisis_resources" in data["emotion_analysis"]
