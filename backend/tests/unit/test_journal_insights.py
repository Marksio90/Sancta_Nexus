"""Unit tests for JournalInsightsService and insights endpoint logic.

Self-contained: no DB, no LLM, no infra imports.
Tests the service's data-mapping logic and fallback behaviour.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.memory.journal_insights_service import (
    DISCLAIMER,
    JournalInsightsService,
    _combined_session,
    _entries_to_sessions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    mood: str | None = "spokój",
    content: str = "Modlitwa kontemplacyjna.",
    scripture: str | None = "Ps 23,1",
    created_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        mood=mood,
        content=content,
        scripture_reference=scripture,
        created_at=created_at or datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# _entries_to_sessions
# ---------------------------------------------------------------------------

class TestEntriesToSessions:
    def test_maps_mood_to_primary_emotion(self):
        entries = [_make_entry(mood="radość")]
        sessions = _entries_to_sessions(entries)
        assert sessions[0]["primary_emotion"] == "radość"

    def test_missing_mood_defaults_to_nieznana(self):
        entries = [_make_entry(mood=None)]
        sessions = _entries_to_sessions(entries)
        assert sessions[0]["primary_emotion"] == "nieznana"

    def test_content_truncated_to_200(self):
        long_content = "x" * 500
        entries = [_make_entry(content=long_content)]
        sessions = _entries_to_sessions(entries)
        assert len(sessions[0]["text"]) == 200

    def test_scripture_ref_mapped(self):
        entries = [_make_entry(scripture="J 15,5")]
        sessions = _entries_to_sessions(entries)
        assert sessions[0]["scripture_ref"] == "J 15,5"

    def test_missing_scripture_is_empty_string(self):
        entries = [_make_entry(scripture=None)]
        sessions = _entries_to_sessions(entries)
        assert sessions[0]["scripture_ref"] == ""

    def test_date_formatted_as_iso(self):
        entries = [_make_entry(created_at=datetime(2026, 3, 5, tzinfo=timezone.utc))]
        sessions = _entries_to_sessions(entries)
        assert sessions[0]["date"] == "2026-03-05"

    def test_empty_entries_returns_empty_list(self):
        assert _entries_to_sessions([]) == []


# ---------------------------------------------------------------------------
# _combined_session
# ---------------------------------------------------------------------------

class TestCombinedSession:
    def test_uses_first_mood_as_primary(self):
        entries = [_make_entry(mood="smutek"), _make_entry(mood="pokuta")]
        session = _combined_session(entries)
        assert session["emotions"]["primary"] == "smutek"

    def test_no_mood_defaults(self):
        entries = [_make_entry(mood=None)]
        session = _combined_session(entries)
        assert session["emotions"]["primary"] == "nieznana"

    def test_uses_first_scripture(self):
        entries = [_make_entry(scripture="Iz 41,10"), _make_entry(scripture="J 14,27")]
        session = _combined_session(entries)
        assert session["scripture"] == "Iz 41,10"

    def test_reflection_built_from_last_5(self):
        entries = [_make_entry(content=f"Wpis {i}") for i in range(10)]
        session = _combined_session(entries)
        assert len(session["reflection"]) <= 500
        # should include content from last 5 entries (5-9)
        assert "Wpis 9" in session["reflection"]

    def test_empty_entries_returns_defaults(self):
        session = _combined_session([])
        assert session["emotions"]["primary"] == "nieznana"
        assert session["scripture"] == ""


# ---------------------------------------------------------------------------
# JournalInsightsService.generate
# ---------------------------------------------------------------------------

class TestJournalInsightsServiceGenerate:
    async def test_returns_required_keys(self):
        entries = [_make_entry()]
        mock_journey = {
            "current_stage": "illumination",
            "stage_name_pl": "Oświecenie",
            "stage_description": "Wzrost",
            "progress_percentage": 50,
            "milestones": [],
            "next_growth_area": "Kontemplacja",
        }
        mock_patterns = [{"type": "grace_moment", "description": "Przełom"}]

        with patch("app.core.llm.get_llm_fast", return_value=None):
            with patch(
                "app.agents.memory.journey_tracker.JourneyTrackerAgent"
            ) as MockTracker:
                tracker_inst = MockTracker.return_value
                tracker_inst.track = AsyncMock(return_value=mock_journey)

                with patch(
                    "app.agents.memory.pattern_discovery.PatternDiscoveryAgent"
                ) as MockDisc:
                    disc_inst = MockDisc.return_value
                    disc_inst.discover = AsyncMock(return_value=mock_patterns)

                    svc = JournalInsightsService()
                    result = await svc.generate("user-1", entries)

        assert "journey" in result
        assert "patterns" in result
        assert "entry_count" in result
        assert "generated_at" in result
        assert "disclaimer" in result
        assert result["entry_count"] == 1
        assert result["disclaimer"] == DISCLAIMER

    async def test_journey_fallback_on_agent_error(self):
        entries = [_make_entry()]
        with patch(
            "app.agents.memory.journey_tracker.JourneyTrackerAgent",
            side_effect=RuntimeError("LLM down"),
        ):
            with patch(
                "app.agents.memory.pattern_discovery.PatternDiscoveryAgent"
            ) as MockDisc:
                disc_inst = MockDisc.return_value
                disc_inst.discover = AsyncMock(return_value=[])

                svc = JournalInsightsService()
                result = await svc.generate("user-1", entries)

        # Should not raise; journey has defaults
        assert result["journey"]["current_stage"] == "purgation"

    async def test_patterns_fallback_on_agent_error(self):
        entries = [_make_entry()]
        mock_journey = {
            "current_stage": "illumination", "stage_name_pl": "Oświecenie",
            "stage_description": "", "progress_percentage": 40,
            "milestones": [], "next_growth_area": "",
        }
        with patch(
            "app.agents.memory.journey_tracker.JourneyTrackerAgent"
        ) as MockTracker:
            tracker_inst = MockTracker.return_value
            tracker_inst.track = AsyncMock(return_value=mock_journey)

            with patch(
                "app.agents.memory.pattern_discovery.PatternDiscoveryAgent",
                side_effect=RuntimeError("LLM down"),
            ):
                svc = JournalInsightsService()
                result = await svc.generate("user-1", entries)

        assert result["patterns"] == []

    async def test_disclaimer_always_present(self):
        entries = [_make_entry()]
        with patch(
            "app.agents.memory.journey_tracker.JourneyTrackerAgent",
            side_effect=RuntimeError("down"),
        ):
            with patch(
                "app.agents.memory.pattern_discovery.PatternDiscoveryAgent",
                side_effect=RuntimeError("down"),
            ):
                svc = JournalInsightsService()
                result = await svc.generate("user-1", entries)

        assert "asystent refleksji" in result["disclaimer"].lower() or \
               "kierownika duchowego" in result["disclaimer"].lower()
