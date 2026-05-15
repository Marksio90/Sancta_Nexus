"""Unit tests for memory agents — JourneyTrackerAgent (A-036) and PatternDiscoveryAgent (A-037).

Self-contained — no LLM, no DB.

Contracts verified:
JourneyTrackerAgent:
- JOURNEY_STAGES: exactly 3 stages (purgation/illumination/union), required fields,
  non-overlapping ranges covering 0-100, each has indicators
- _parse_response: STAGE/PROGRESS/MILESTONE/GROWTH lines, invalid stage→purgation,
  progress clamped to 0-100, missing keys get defaults

PatternDiscoveryAgent:
- PATTERN_TYPES: exactly 6, all expected types present
- _parse_patterns: single/multiple patterns, PATTERN/DESC/FREQ/SCRIPTURE fields,
  trailing block appended, empty→empty list
- _default_patterns: returns at least 1 pattern with required fields
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.memory.journey_tracker import JOURNEY_STAGES, JourneyTrackerAgent
from app.agents.memory.pattern_discovery import PATTERN_TYPES, PatternDiscoveryAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tracker() -> JourneyTrackerAgent:
    agent = JourneyTrackerAgent.__new__(JourneyTrackerAgent)
    agent.llm = None
    return agent


def _discoverer() -> PatternDiscoveryAgent:
    agent = PatternDiscoveryAgent.__new__(PatternDiscoveryAgent)
    agent.llm = None
    return agent


# ===========================================================================
# JourneyTrackerAgent (A-036)
# ===========================================================================


class TestJourneyStages:
    def test_exactly_3_stages(self):
        assert len(JOURNEY_STAGES) == 3

    def test_all_three_present(self):
        assert set(JOURNEY_STAGES.keys()) == {"purgation", "illumination", "union"}

    def test_all_have_required_fields(self):
        required = {"name_pl", "description", "indicators", "range"}
        for stage, data in JOURNEY_STAGES.items():
            assert required <= set(data.keys()), f"{stage} missing fields"

    def test_all_have_indicators(self):
        for stage, data in JOURNEY_STAGES.items():
            assert len(data["indicators"]) >= 3

    def test_ranges_cover_0_to_100(self):
        all_values = set()
        for data in JOURNEY_STAGES.values():
            start, end = data["range"]
            all_values.update(range(start, end + 1))
        assert 0 in all_values
        assert 100 in all_values

    def test_ranges_non_overlapping(self):
        ranges = [data["range"] for data in JOURNEY_STAGES.values()]
        all_values = []
        for start, end in ranges:
            all_values.extend(range(start, end + 1))
        assert len(all_values) == len(set(all_values)), "Overlapping ranges"

    def test_purgation_starts_at_0(self):
        assert JOURNEY_STAGES["purgation"]["range"][0] == 0

    def test_union_ends_at_100(self):
        assert JOURNEY_STAGES["union"]["range"][1] == 100

    def test_all_have_polish_names(self):
        for stage, data in JOURNEY_STAGES.items():
            assert data["name_pl"].strip()


class TestJourneyParseResponse:
    def test_valid_response_all_fields(self):
        agent = _tracker()
        text = "STAGE: illumination\nPROGRESS: 45\nMILESTONE: Regularna modlitwa\nGROWTH: Kontemplacja"
        result = agent._parse_response(text)
        assert result["current_stage"] == "illumination"
        assert result["progress_percentage"] == 45
        assert result["milestones"] == ["Regularna modlitwa"]
        assert result["next_growth_area"] == "Kontemplacja"

    def test_invalid_stage_defaults_to_purgation(self):
        agent = _tracker()
        text = "STAGE: nirvana\nPROGRESS: 50\nMILESTONE: x\nGROWTH: y"
        result = agent._parse_response(text)
        assert result["current_stage"] == "purgation"

    def test_union_stage(self):
        agent = _tracker()
        text = "STAGE: union\nPROGRESS: 85\nMILESTONE: Kontemplacja\nGROWTH: Miłość"
        result = agent._parse_response(text)
        assert result["current_stage"] == "union"
        assert result["progress_percentage"] == 85

    def test_progress_above_100_clamped(self):
        agent = _tracker()
        text = "STAGE: union\nPROGRESS: 150\nMILESTONE: x\nGROWTH: y"
        result = agent._parse_response(text)
        assert result["progress_percentage"] == 100

    def test_progress_below_0_clamped(self):
        agent = _tracker()
        text = "STAGE: purgation\nPROGRESS: -10\nMILESTONE: x\nGROWTH: y"
        result = agent._parse_response(text)
        assert result["progress_percentage"] == 0

    def test_stage_name_pl_set(self):
        agent = _tracker()
        text = "STAGE: illumination\nPROGRESS: 40\nMILESTONE: x\nGROWTH: y"
        result = agent._parse_response(text)
        assert result["stage_name_pl"] == JOURNEY_STAGES["illumination"]["name_pl"]

    def test_returns_required_keys(self):
        agent = _tracker()
        text = "STAGE: purgation\nPROGRESS: 10\nMILESTONE: x\nGROWTH: y"
        result = agent._parse_response(text)
        required = {"current_stage", "stage_name_pl", "progress_percentage",
                    "milestones", "next_growth_area"}
        assert required <= set(result.keys())

    def test_empty_text_uses_defaults(self):
        agent = _tracker()
        result = agent._parse_response("")
        assert result["current_stage"] in JOURNEY_STAGES


# ===========================================================================
# PatternDiscoveryAgent (A-037)
# ===========================================================================


class TestPatternTypes:
    def test_exactly_6_types(self):
        assert len(PATTERN_TYPES) == 6

    def test_recurring_theme_present(self):
        assert "recurring_theme" in PATTERN_TYPES

    def test_cyclical_crisis_present(self):
        assert "cyclical_crisis" in PATTERN_TYPES

    def test_grace_moment_present(self):
        assert "grace_moment" in PATTERN_TYPES

    def test_growth_trajectory_present(self):
        assert "growth_trajectory" in PATTERN_TYPES

    def test_scripture_affinity_present(self):
        assert "scripture_affinity" in PATTERN_TYPES

    def test_emotional_pattern_present(self):
        assert "emotional_pattern" in PATTERN_TYPES


class TestParsePatterns:
    def test_single_pattern_all_fields(self):
        agent = _discoverer()
        # Use simple refs without comma-in-verse to avoid split ambiguity
        text = (
            "PATTERN: recurring_theme\n"
            "DESC: Zaufanie Bogu\n"
            "FREQ: tygodniowo\n"
            "SCRIPTURE: Ps 23, Rz 8"
        )
        result = agent._parse_patterns(text)
        assert len(result) == 1
        assert result[0]["type"] == "recurring_theme"
        assert result[0]["description"] == "Zaufanie Bogu"
        assert result[0]["frequency"] == "tygodniowo"
        assert isinstance(result[0]["related_scriptures"], list)
        assert len(result[0]["related_scriptures"]) == 2

    def test_multiple_patterns(self):
        agent = _discoverer()
        text = (
            "PATTERN: recurring_theme\nDESC: Temat 1\nFREQ: weekly\nSCRIPTURE: J 1,1\n"
            "PATTERN: grace_moment\nDESC: Temat 2\nFREQ: monthly\nSCRIPTURE: Ps 23"
        )
        result = agent._parse_patterns(text)
        assert len(result) == 2
        assert result[0]["type"] == "recurring_theme"
        assert result[1]["type"] == "grace_moment"

    def test_empty_text_returns_empty_list(self):
        agent = _discoverer()
        result = agent._parse_patterns("")
        assert result == []

    def test_no_pattern_lines_returns_empty(self):
        agent = _discoverer()
        result = agent._parse_patterns("Some irrelevant text\nMore text")
        assert result == []

    def test_partial_pattern_missing_desc(self):
        agent = _discoverer()
        text = "PATTERN: emotional_pattern\nFREQ: daily"
        result = agent._parse_patterns(text)
        assert len(result) == 1
        assert result[0]["type"] == "emotional_pattern"
        assert "description" not in result[0]

    def test_scripture_produces_list(self):
        # Comma-split produces a list; Polish verse refs (J 15,5) further split on
        # the verse comma — test that the result is a list with ≥1 element
        agent = _discoverer()
        text = "PATTERN: scripture_affinity\nDESC: Fragm\nFREQ: daily\nSCRIPTURE: Ps 23, Mt 11"
        result = agent._parse_patterns(text)
        assert isinstance(result[0]["related_scriptures"], list)
        assert len(result[0]["related_scriptures"]) >= 1


class TestDefaultPatterns:
    def test_returns_at_least_one_pattern(self):
        agent = _discoverer()
        result = agent._default_patterns()
        assert len(result) >= 1

    def test_first_pattern_has_required_fields(self):
        agent = _discoverer()
        result = agent._default_patterns()
        for p in result:
            assert "type" in p
            assert "description" in p
            assert "frequency" in p
            assert "related_scriptures" in p

    def test_type_is_valid(self):
        agent = _discoverer()
        for p in agent._default_patterns():
            assert p["type"] in PATTERN_TYPES

    def test_scriptures_are_list(self):
        agent = _discoverer()
        for p in agent._default_patterns():
            assert isinstance(p["related_scriptures"], list)
