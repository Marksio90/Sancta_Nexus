"""Unit tests for doctrine guard and spiritual state classifier.

Two critical safety components tested without LLM calls:
  - DoctrineGuardAgent (A-021): DOGMAS catalog, _parse_violations, _parse_confidence,
    _format_dogmas
  - SpiritualStateClassifier (A-025): SpiritualStateEnum, SpiritualState dataclass,
    _build_user_prompt, _parse_response

Both agents bypass __init__ to avoid OpenAI/config imports.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.agents.theology.doctrine_guard import (
    DOGMAS,
    DoctrineGuardAgent,
)
from app.agents.emotion.spiritual_state_classifier import (
    SpiritualState,
    SpiritualStateClassifier,
    SpiritualStateEnum,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doctrine_agent() -> DoctrineGuardAgent:
    agent = DoctrineGuardAgent.__new__(DoctrineGuardAgent)
    agent._llm = None
    agent._dogmas = DOGMAS
    return agent


def _classifier() -> SpiritualStateClassifier:
    agent = SpiritualStateClassifier.__new__(SpiritualStateClassifier)
    agent._llm = None
    return agent


# ===========================================================================
# DoctrineGuardAgent (A-021) — DOGMAS catalog
# ===========================================================================


class TestDogmasCatalog:
    def test_exactly_47_dogmas(self):
        assert len(DOGMAS) == 47

    def test_all_have_required_fields(self):
        required = {"id", "category", "label", "desc"}
        for d in DOGMAS:
            assert required <= set(d.keys()), f"Missing field in dogma {d.get('id')}"

    def test_unique_ids(self):
        ids = [d["id"] for d in DOGMAS]
        assert len(ids) == len(set(ids)), "Duplicate dogma IDs"

    def test_all_fields_non_empty(self):
        for d in DOGMAS:
            assert d["id"].strip()
            assert d["category"].strip()
            assert d["label"].strip()
            assert d["desc"].strip()

    def test_trinity_dogmas_present(self):
        ids = {d["id"] for d in DOGMAS}
        assert "T-01" in ids  # One God
        assert "T-02" in ids  # Trinity of Persons

    def test_eucharist_real_presence_present(self):
        ids = {d["id"] for d in DOGMAS}
        assert "E-01" in ids  # Real Presence

    def test_mary_dogmas_present(self):
        ids = {d["id"] for d in DOGMAS}
        assert "M-01" in ids  # Theotokos
        assert "M-02" in ids  # Immaculate Conception
        assert "M-04" in ids  # Assumption

    def test_christology_dogmas_present(self):
        ids = {d["id"] for d in DOGMAS}
        assert "C-01" in ids  # True God and True Man
        assert "C-04" in ids  # Bodily Resurrection

    def test_categories_cover_key_areas(self):
        categories = {d["category"] for d in DOGMAS}
        for cat in ("Trinity", "Incarnation", "Eucharist", "Mary", "Salvation"):
            assert cat in categories

    def test_papal_infallibility_present(self):
        ids = {d["id"] for d in DOGMAS}
        assert "CH-03" in ids  # Papal Infallibility


class TestFormatDogmas:
    def test_returns_string(self):
        agent = _doctrine_agent()
        result = agent._format_dogmas()
        assert isinstance(result, str)

    def test_contains_all_dogma_ids(self):
        agent = _doctrine_agent()
        result = agent._format_dogmas()
        for d in DOGMAS:
            assert d["id"] in result

    def test_contains_all_labels(self):
        agent = _doctrine_agent()
        result = agent._format_dogmas()
        for d in DOGMAS:
            assert d["label"] in result

    def test_format_includes_category(self):
        agent = _doctrine_agent()
        result = agent._format_dogmas()
        assert "Trinity" in result
        assert "Eucharist" in result


class TestParseViolations:
    def test_no_violations_keyword(self):
        result = DoctrineGuardAgent._parse_violations("NO_VIOLATIONS")
        assert result == []

    def test_no_violations_lowercase(self):
        result = DoctrineGuardAgent._parse_violations("no_violations")
        assert result == []

    def test_single_violation(self):
        raw = "VIOLATION|T-02|The text denies the Trinity."
        result = DoctrineGuardAgent._parse_violations(raw)
        assert len(result) == 1
        assert "T-02" in result[0]
        assert "Trinity" in result[0]

    def test_multiple_violations(self):
        raw = "VIOLATION|T-02|Denies Trinity.\nVIOLATION|E-01|Denies Real Presence."
        result = DoctrineGuardAgent._parse_violations(raw)
        assert len(result) == 2

    def test_violation_without_explanation(self):
        raw = "VIOLATION|M-04"
        result = DoctrineGuardAgent._parse_violations(raw)
        assert len(result) == 1
        assert "M-04" in result[0]

    def test_unexpected_format_fails_closed(self):
        """Unknown format without NO_VIOLATIONS → fail closed (1 violation added)."""
        result = DoctrineGuardAgent._parse_violations("The content is questionable.")
        assert len(result) >= 1
        assert any("parse" in r.lower() or "review" in r.lower() for r in result)

    def test_empty_response_fails_closed(self):
        result = DoctrineGuardAgent._parse_violations("")
        assert len(result) >= 1

    def test_mixed_valid_and_invalid_lines(self):
        raw = "Some intro text\nVIOLATION|C-01|Denies hypostatic union.\nMore text"
        result = DoctrineGuardAgent._parse_violations(raw)
        assert any("C-01" in r for r in result)


class TestParseConfidence:
    def test_valid_confidence_line(self):
        raw = "NO_VIOLATIONS\nCONFIDENCE|0.95"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == pytest.approx(0.95, abs=0.001)

    def test_lowercase_confidence(self):
        raw = "NO_VIOLATIONS\nconfidence|0.8"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == pytest.approx(0.8, abs=0.001)

    def test_clamps_above_1(self):
        raw = "CONFIDENCE|1.5"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == 1.0

    def test_clamps_below_0(self):
        raw = "CONFIDENCE|-0.5"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == 0.0

    def test_default_for_no_violations(self):
        """If no CONFIDENCE line, defaults to 0.9 when NO_VIOLATIONS present."""
        raw = "NO_VIOLATIONS"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == 0.9

    def test_default_for_violations(self):
        """If no CONFIDENCE line and violations, defaults to 0.5."""
        raw = "VIOLATION|T-01|Something wrong"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == 0.5

    def test_invalid_float_uses_default(self):
        raw = "CONFIDENCE|not_a_number\nNO_VIOLATIONS"
        result = DoctrineGuardAgent._parse_confidence(raw)
        assert result == 0.9  # no_violations default


# ===========================================================================
# SpiritualStateClassifier (A-025)
# ===========================================================================


class TestSpiritualStateEnum:
    def test_has_8_states(self):
        assert len(SpiritualStateEnum) == 8

    def test_dark_night(self):
        assert SpiritualStateEnum.DARK_NIGHT == "dark_night"

    def test_consolation(self):
        assert SpiritualStateEnum.CONSOLATION == "consolation"

    def test_desolation(self):
        assert SpiritualStateEnum.DESOLATION == "desolation"

    def test_dryness(self):
        assert SpiritualStateEnum.DRYNESS == "dryness"

    def test_fervor(self):
        assert SpiritualStateEnum.FERVOR == "fervor"

    def test_peace(self):
        assert SpiritualStateEnum.PEACE == "peace"

    def test_temptation(self):
        assert SpiritualStateEnum.TEMPTATION == "temptation"

    def test_growth(self):
        assert SpiritualStateEnum.GROWTH == "growth"


class TestSpiritualStateDataclass:
    def test_is_frozen(self):
        state = SpiritualState(primary_state=SpiritualStateEnum.PEACE, confidence=0.9)
        with pytest.raises((AttributeError, TypeError)):
            state.confidence = 0.1  # type: ignore[misc]

    def test_required_fields(self):
        state = SpiritualState(primary_state=SpiritualStateEnum.CONSOLATION, confidence=0.8)
        assert state.primary_state == SpiritualStateEnum.CONSOLATION
        assert state.confidence == 0.8

    def test_optional_secondary_state_defaults_none(self):
        state = SpiritualState(primary_state=SpiritualStateEnum.PEACE, confidence=0.7)
        assert state.secondary_state is None

    def test_optional_string_fields_default_empty(self):
        state = SpiritualState(primary_state=SpiritualStateEnum.PEACE, confidence=0.7)
        assert state.description == ""
        assert state.ignatian_rule == ""
        assert state.recommended_response == ""


class TestBuildUserPrompt:
    def test_contains_emotion_vector(self):
        agent = _classifier()
        vector = {"joy": 0.8, "peace": 0.7}
        result = agent._build_user_prompt(vector, [])
        assert "joy" in result
        assert "peace" in result

    def test_empty_history_shows_no_history(self):
        agent = _classifier()
        result = agent._build_user_prompt({"joy": 0.5}, [])
        assert "No prior history" in result

    def test_history_included(self):
        agent = _classifier()
        history = [{"text": "I feel grateful today", "timestamp": "2024-01-01", "spiritual_state": "consolation"}]
        result = agent._build_user_prompt({"joy": 0.5}, history)
        assert "grateful" in result

    def test_history_limited_to_10(self):
        agent = _classifier()
        history = [
            {"text": f"Entry {i}", "timestamp": f"2024-01-{i:02d}", "spiritual_state": "peace"}
            for i in range(15)
        ]
        result = agent._build_user_prompt({"joy": 0.5}, history)
        # Only last 10 entries; first 5 should not appear
        assert "Entry 0" not in result
        assert "Entry 14" in result

    def test_emotions_sorted_descending(self):
        agent = _classifier()
        vector = {"sadness": 0.3, "joy": 0.9, "fear": 0.1}
        result = agent._build_user_prompt(vector, [])
        # joy (0.9) should appear before sadness (0.3) in the output
        joy_pos = result.index("joy")
        sadness_pos = result.index("sadness")
        assert joy_pos < sadness_pos


class TestParseResponse:
    def test_valid_json_consolation(self):
        agent = _classifier()
        raw = json.dumps({
            "primary_state": "consolation",
            "confidence": 0.85,
            "secondary_state": None,
            "description": "User shows signs of spiritual consolation.",
            "ignatian_rule": "SpEx 316",
            "recommended_response": "Encourage journaling.",
        })
        result = agent._parse_response(raw)
        assert result.primary_state == SpiritualStateEnum.CONSOLATION
        assert result.confidence == pytest.approx(0.85, abs=0.001)

    def test_invalid_primary_state_defaults_to_peace(self):
        agent = _classifier()
        raw = json.dumps({"primary_state": "unknown_state", "confidence": 0.5})
        result = agent._parse_response(raw)
        assert result.primary_state == SpiritualStateEnum.PEACE

    def test_secondary_state_parsed(self):
        agent = _classifier()
        raw = json.dumps({
            "primary_state": "desolation",
            "secondary_state": "dryness",
            "confidence": 0.7,
        })
        result = agent._parse_response(raw)
        assert result.secondary_state == SpiritualStateEnum.DRYNESS

    def test_invalid_secondary_state_is_none(self):
        agent = _classifier()
        raw = json.dumps({
            "primary_state": "peace",
            "secondary_state": "invalid_state",
            "confidence": 0.8,
        })
        result = agent._parse_response(raw)
        assert result.secondary_state is None

    def test_confidence_clamped_above_1(self):
        agent = _classifier()
        raw = json.dumps({"primary_state": "peace", "confidence": 2.5})
        result = agent._parse_response(raw)
        assert result.confidence == 1.0

    def test_confidence_clamped_below_0(self):
        agent = _classifier()
        raw = json.dumps({"primary_state": "peace", "confidence": -0.5})
        result = agent._parse_response(raw)
        assert result.confidence == 0.0

    def test_malformed_json_returns_peace_with_zero_confidence(self):
        agent = _classifier()
        result = agent._parse_response("not valid json")
        assert result.primary_state == SpiritualStateEnum.PEACE
        assert result.confidence == 0.0

    def test_markdown_fence_stripped(self):
        agent = _classifier()
        raw = '```json\n{"primary_state": "fervor", "confidence": 0.9}\n```'
        result = agent._parse_response(raw)
        assert result.primary_state == SpiritualStateEnum.FERVOR

    def test_description_preserved(self):
        agent = _classifier()
        raw = json.dumps({
            "primary_state": "consolation",
            "confidence": 0.8,
            "description": "Strong consolation detected.",
        })
        result = agent._parse_response(raw)
        assert result.description == "Strong consolation detected."
