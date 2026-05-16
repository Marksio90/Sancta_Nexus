"""Unit tests for JourneyTrackerAgent (A-036)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.memory.journey_tracker import JourneyTrackerAgent

SESSION_DATA = {
    "emotions": {"primary": "peace"},
    "spiritual_state": "illumination",
    "reflection": "Modlitwa kontemplacyjna",
    "scripture": "Ps 23,1",
}


def _make_llm(response_content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=response_content))
    return llm


async def test_track_returns_expected_keys():
    mock_llm = _make_llm(
        "STAGE: illumination\nPROGRESS: 45\nMILESTONE: Regularna modlitwa\nGROWTH: Kontemplacja"
    )
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm):
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
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm):
        tracker = JourneyTrackerAgent()
        result = await tracker.track("user-123", SESSION_DATA)

    assert result["current_stage"] == "purgation"
    assert result["progress_percentage"] == 15
    assert "next_growth_area" in result


async def test_track_clamps_progress_percentage():
    mock_llm = _make_llm("STAGE: union\nPROGRESS: 999\nMILESTONE: test\nGROWTH: more")
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm):
        tracker = JourneyTrackerAgent()
        result = await tracker.track("user-123", SESSION_DATA)

    assert result["progress_percentage"] == 100


def test_tracker_uses_llm_factory():
    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm) as mock_factory:
        JourneyTrackerAgent()
        mock_factory.assert_called_once()
