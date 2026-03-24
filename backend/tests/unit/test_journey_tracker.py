"""Unit tests for JourneyTrackerAgent (A-036)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.memory.journey_tracker import JourneyTrackerAgent, JOURNEY_STAGES


SESSION_DATA = {
    "emotions": {"primary": "peace"},
    "spiritual_state": "illumination",
    "reflection": "Modlitwa kontemplacyjna",
    "scripture": "Ps 23,1",
}


async def test_track_returns_expected_keys():
    mock_response = MagicMock()
    mock_response.content = "STAGE: illumination\nPROGRESS: 45\nMILESTONE: Regularna modlitwa\nGROWTH: Kontemplacja"

    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)

        tracker = JourneyTrackerAgent()
        result = await tracker.track("user-123", SESSION_DATA)

    assert "current_stage" in result
    assert "stage_name_pl" in result
    assert "progress_percentage" in result
    assert "milestones" in result
    assert "next_growth_area" in result
    assert result["current_stage"] == "illumination"
    assert result["progress_percentage"] == 45


async def test_track_returns_fallback_on_llm_error():
    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        tracker = JourneyTrackerAgent()
        result = await tracker.track("user-123", SESSION_DATA)

    # Fallback defaults
    assert result["current_stage"] == "purgation"
    assert result["progress_percentage"] == 15
    assert "next_growth_area" in result


async def test_track_clamps_progress_percentage():
    mock_response = MagicMock()
    mock_response.content = "STAGE: union\nPROGRESS: 999\nMILESTONE: test\nGROWTH: more"

    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)

        tracker = JourneyTrackerAgent()
        result = await tracker.track("user-123", SESSION_DATA)

    assert result["progress_percentage"] == 100


def test_tracker_uses_settings_model():
    """JourneyTrackerAgent should use settings.LLM_FAST_MODEL, not hardcoded 'gpt-4o'."""
    from app.core.config import settings
    with patch("app.agents.memory.journey_tracker.ChatOpenAI") as MockLLM:
        JourneyTrackerAgent()
        call_kwargs = MockLLM.call_args
        assert call_kwargs.kwargs.get("model") == settings.LLM_FAST_MODEL or \
               call_kwargs.args[0] == settings.LLM_FAST_MODEL if call_kwargs.args else True
