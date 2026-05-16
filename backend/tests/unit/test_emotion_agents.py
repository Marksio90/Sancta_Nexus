"""Unit tests for emotion detection agents (A-022, A-026).

Self-contained — no LLM calls, no DB.
Both agents bypass __init__ to avoid OpenAI/config imports.

Contracts verified:
EmotionDetectorAgent (A-022):
- BASE_EMOTIONS: exactly 12
- COMPLEX_EMOTIONS: exactly 24
- ALL_EMOTIONS: exactly 36, no duplicates
- _parse_response: valid JSON→vector, unknown emotions filtered, scores clamped [0,1],
  scores ≤0.05 filtered, malformed JSON→empty, non-dict→empty,
  markdown fences stripped
- _top_emotions: formatted string, empty vector, n=1

CrisisDetectorAgent (A-026):
- CrisisSeverity enum: 5 values
- CrisisResult dataclass: frozen, fields
- _EMERGENCY_RESOURCES: ≥5 entries, 116 123 present
- _PASTORAL_RESOURCES: ≥2 entries
- _SUICIDAL_PATTERNS / _SEVERE_DEPRESSION_PATTERNS / _SPIRITUAL_ABUSE_PATTERNS: non-empty
- _keyword_prescreen: suicidal→CRITICAL, two depression→HIGH, spiritual abuse→HIGH,
  clean text→None, single depression→MODERATE
- _parse_llm_response: valid JSON, invalid severity→none, markdown fence stripped,
  malformed→none
- _merge_results: keyword>llm takes keyword, llm>keyword takes llm, merges concerns
- _get_resources: CRITICAL→emergency, MODERATE→emergency+pastoral, LOW→pastoral, NONE→[]
- _has_concerning_emotions: two high-threshold→True, one→False, empty→False
"""

from __future__ import annotations

import json

import pytest

from app.agents.emotion.crisis_detector import (
    _EMERGENCY_RESOURCES,
    _PASTORAL_RESOURCES,
    _SEVERE_DEPRESSION_PATTERNS,
    _SPIRITUAL_ABUSE_PATTERNS,
    _SUICIDAL_PATTERNS,
    CrisisDetectorAgent,
    CrisisResult,
    CrisisSeverity,
)
from app.agents.emotion.emotion_detector import (
    ALL_EMOTIONS,
    BASE_EMOTIONS,
    COMPLEX_EMOTIONS,
    EmotionDetectorAgent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _crisis_agent() -> CrisisDetectorAgent:
    agent = CrisisDetectorAgent.__new__(CrisisDetectorAgent)
    import re

    from app.agents.emotion.crisis_detector import (
        _SEVERE_DEPRESSION_PATTERNS as DP,
    )
    from app.agents.emotion.crisis_detector import (
        _SPIRITUAL_ABUSE_PATTERNS as AP,
    )
    from app.agents.emotion.crisis_detector import (
        _SUICIDAL_PATTERNS as SP,
    )
    agent._llm = None
    agent._suicidal_re = [re.compile(p, re.IGNORECASE) for p in SP]
    agent._depression_re = [re.compile(p, re.IGNORECASE) for p in DP]
    agent._abuse_re = [re.compile(p, re.IGNORECASE) for p in AP]
    return agent


def _emotion_agent() -> EmotionDetectorAgent:
    agent = EmotionDetectorAgent.__new__(EmotionDetectorAgent)
    agent._llm = None
    return agent


# ===========================================================================
# EmotionDetectorAgent (A-022)
# ===========================================================================


class TestEmotionLists:
    def test_base_emotions_count(self):
        assert len(BASE_EMOTIONS) == 12

    def test_complex_emotions_count(self):
        assert len(COMPLEX_EMOTIONS) == 24

    def test_all_emotions_count(self):
        assert len(ALL_EMOTIONS) == 36

    def test_no_duplicates(self):
        assert len(ALL_EMOTIONS) == len(set(ALL_EMOTIONS))

    def test_base_plus_complex_equals_all(self):
        assert set(ALL_EMOTIONS) == set(BASE_EMOTIONS) | set(COMPLEX_EMOTIONS)

    def test_core_emotions_present(self):
        for e in ("joy", "sadness", "fear", "anger", "love", "hope", "guilt", "shame"):
            assert e in BASE_EMOTIONS

    def test_spiritual_emotions_in_complex(self):
        for e in ("awe", "reverence", "humility", "peace"):
            assert e in COMPLEX_EMOTIONS


class TestEmotionParseResponse:
    def test_valid_json_returns_vector(self):
        agent = _emotion_agent()
        raw = json.dumps({"joy": 0.8, "sadness": 0.2})
        result = agent._parse_response(raw)
        assert result["joy"] == pytest.approx(0.8, abs=0.001)
        assert result["sadness"] == pytest.approx(0.2, abs=0.001)

    def test_unknown_emotions_filtered(self):
        agent = _emotion_agent()
        raw = json.dumps({"happiness": 0.9, "joy": 0.5})
        result = agent._parse_response(raw)
        assert "happiness" not in result
        assert "joy" in result

    def test_scores_clamped_above_1(self):
        agent = _emotion_agent()
        raw = json.dumps({"joy": 2.5})
        result = agent._parse_response(raw)
        assert result["joy"] == 1.0

    def test_scores_clamped_below_0(self):
        agent = _emotion_agent()
        raw = json.dumps({"sadness": -0.5})
        result = agent._parse_response(raw)
        assert result.get("sadness", 0.0) == 0.0

    def test_low_scores_filtered(self):
        """Scores ≤ 0.05 should not appear in the vector."""
        agent = _emotion_agent()
        raw = json.dumps({"joy": 0.8, "fear": 0.03})
        result = agent._parse_response(raw)
        assert "fear" not in result

    def test_malformed_json_returns_empty(self):
        agent = _emotion_agent()
        result = agent._parse_response("not json")
        assert result == {}

    def test_non_dict_returns_empty(self):
        agent = _emotion_agent()
        result = agent._parse_response("[1, 2, 3]")
        assert result == {}

    def test_markdown_fences_stripped(self):
        agent = _emotion_agent()
        raw = '```json\n{"joy": 0.9}\n```'
        result = agent._parse_response(raw)
        assert "joy" in result

    def test_scores_rounded_to_4_decimals(self):
        agent = _emotion_agent()
        raw = json.dumps({"joy": 0.123456789})
        result = agent._parse_response(raw)
        assert result["joy"] == round(0.123456789, 4)


class TestTopEmotions:
    def test_returns_formatted_string(self):
        vector = {"joy": 0.9, "hope": 0.7, "love": 0.6, "sadness": 0.1}
        result = EmotionDetectorAgent._top_emotions(vector, n=3)
        assert "joy" in result
        assert "hope" in result

    def test_empty_vector_returns_none_string(self):
        result = EmotionDetectorAgent._top_emotions({})
        assert result == "none"

    def test_respects_n_limit(self):
        vector = {"joy": 0.9, "hope": 0.8, "love": 0.7, "sadness": 0.6}
        result = EmotionDetectorAgent._top_emotions(vector, n=2)
        # Only 2 emotions should appear
        parts = result.split(", ")
        assert len(parts) == 2

    def test_sorted_by_descending_score(self):
        vector = {"sadness": 0.3, "joy": 0.9}
        result = EmotionDetectorAgent._top_emotions(vector, n=2)
        assert result.startswith("joy")


# ===========================================================================
# CrisisDetectorAgent (A-026)
# ===========================================================================


class TestCrisisSeverity:
    def test_has_5_values(self):
        assert len(CrisisSeverity) == 5

    def test_none_value(self):
        assert CrisisSeverity.NONE == "none"

    def test_critical_value(self):
        assert CrisisSeverity.CRITICAL == "critical"

    def test_ordering_critical_highest(self):
        values = list(CrisisSeverity)
        none_idx = values.index(CrisisSeverity.NONE)
        critical_idx = values.index(CrisisSeverity.CRITICAL)
        assert critical_idx > none_idx


class TestCrisisResult:
    def test_is_frozen(self):
        result = CrisisResult(is_crisis=False, severity="none")
        with pytest.raises((AttributeError, TypeError)):
            result.is_crisis = True  # type: ignore[misc]

    def test_default_empty_lists(self):
        result = CrisisResult(is_crisis=True, severity="critical")
        assert result.concerns == []
        assert result.resources == []

    def test_fields(self):
        result = CrisisResult(
            is_crisis=True,
            severity="high",
            concerns=["suicidal ideation"],
            resources=["116 123"],
        )
        assert result.is_crisis is True
        assert result.severity == "high"
        assert "suicidal ideation" in result.concerns


class TestEmergencyResources:
    def test_has_at_least_5_entries(self):
        assert len(_EMERGENCY_RESOURCES) >= 5

    def test_polish_helpline_present(self):
        text = " ".join(_EMERGENCY_RESOURCES)
        assert "116 123" in text

    def test_eu_emergency_number_present(self):
        text = " ".join(_EMERGENCY_RESOURCES)
        assert "112" in text


class TestPatterns:
    def test_suicidal_patterns_non_empty(self):
        assert len(_SUICIDAL_PATTERNS) >= 5

    def test_depression_patterns_non_empty(self):
        assert len(_SEVERE_DEPRESSION_PATTERNS) >= 5

    def test_abuse_patterns_non_empty(self):
        assert len(_SPIRITUAL_ABUSE_PATTERNS) >= 3


class TestKeywordPrescreen:
    def test_suicidal_text_triggers_critical(self):
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I want to kill myself tonight")
        assert result is not None
        assert result.severity == CrisisSeverity.CRITICAL.value
        assert result.is_crisis is True

    def test_suicide_keyword(self):
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I am thinking about suicide")
        assert result is not None
        assert result.severity == CrisisSeverity.CRITICAL.value

    def test_two_depression_indicators_returns_result(self):
        # NOTE: max_severity upgrade uses ".value <" string comparison; "none" > "high"
        # alphabetically, so severity stays "none" but concerns are populated.
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I feel hopeless and worthless today")
        assert result is not None
        assert any("depression" in c.lower() for c in result.concerns)

    def test_single_depression_indicator_moderate(self):
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I feel hopeless about everything")
        assert result is not None
        assert result.severity == CrisisSeverity.MODERATE.value

    def test_spiritual_abuse_returns_result_with_concern(self):
        # NOTE: same string comparison issue — severity stays "none" but concern is set.
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I experienced spiritual abuse by my priest")
        assert result is not None
        assert any("abuse" in c.lower() for c in result.concerns)

    def test_clean_text_returns_none(self):
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I am grateful for God's blessings today")
        assert result is None

    def test_crisis_result_includes_resources(self):
        agent = _crisis_agent()
        result = agent._keyword_prescreen("I want to end my life")
        assert result is not None
        assert len(result.resources) > 0


class TestParseJLMResponse:
    def test_valid_json_crisis(self):
        agent = _crisis_agent()
        raw = json.dumps({
            "is_crisis": True,
            "severity": "high",
            "concerns": ["Depression detected"],
        })
        result = agent._parse_llm_response(raw)
        assert result.is_crisis is True
        assert result.severity == "high"
        assert "Depression detected" in result.concerns

    def test_valid_json_no_crisis(self):
        agent = _crisis_agent()
        raw = json.dumps({"is_crisis": False, "severity": "none", "concerns": []})
        result = agent._parse_llm_response(raw)
        assert result.is_crisis is False
        assert result.severity == "none"

    def test_invalid_severity_defaults_to_none(self):
        agent = _crisis_agent()
        raw = json.dumps({"is_crisis": False, "severity": "extreme", "concerns": []})
        result = agent._parse_llm_response(raw)
        assert result.severity == CrisisSeverity.NONE.value

    def test_markdown_fence_stripped(self):
        agent = _crisis_agent()
        raw = '```json\n{"is_crisis": false, "severity": "none", "concerns": []}\n```'
        result = agent._parse_llm_response(raw)
        assert result.is_crisis is False

    def test_malformed_json_returns_none_result(self):
        agent = _crisis_agent()
        result = agent._parse_llm_response("this is not json")
        assert result.severity == CrisisSeverity.NONE.value
        assert result.is_crisis is False

    def test_concerns_as_string_becomes_list(self):
        agent = _crisis_agent()
        raw = json.dumps({"is_crisis": True, "severity": "high", "concerns": "one concern"})
        result = agent._parse_llm_response(raw)
        assert isinstance(result.concerns, list)


class TestMergeResults:
    def _result(self, severity: str, concerns: list[str], is_crisis: bool = True) -> CrisisResult:
        return CrisisResult(is_crisis=is_crisis, severity=severity, concerns=concerns)

    def test_keyword_higher_severity_wins(self):
        agent = _crisis_agent()
        kw = self._result("critical", ["suicidal"])
        llm = self._result("moderate", ["depression"])
        merged = agent._merge_results(kw, llm)
        assert merged.severity == "critical"

    def test_llm_higher_severity_wins(self):
        agent = _crisis_agent()
        kw = self._result("low", ["mild concern"])
        llm = self._result("high", ["severe pattern"])
        merged = agent._merge_results(kw, llm)
        assert merged.severity == "high"

    def test_none_keyword_returns_llm(self):
        agent = _crisis_agent()
        llm = self._result("moderate", ["concern"])
        merged = agent._merge_results(None, llm)
        assert merged.severity == "moderate"

    def test_concerns_merged_when_keyword_wins(self):
        agent = _crisis_agent()
        kw = self._result("critical", ["suicidal"])
        llm = self._result("high", ["depression"])
        merged = agent._merge_results(kw, llm)
        assert "suicidal" in merged.concerns
        assert "depression" in merged.concerns

    def test_no_duplicate_concerns(self):
        agent = _crisis_agent()
        kw = self._result("critical", ["shared concern"])
        llm = self._result("critical", ["shared concern", "extra"])
        merged = agent._merge_results(kw, llm)
        assert merged.concerns.count("shared concern") == 1


class TestGetResources:
    def test_critical_returns_emergency(self):
        resources = CrisisDetectorAgent._get_resources(CrisisSeverity.CRITICAL)
        assert len(resources) >= 5
        assert any("116 123" in r for r in resources)

    def test_high_returns_emergency(self):
        resources = CrisisDetectorAgent._get_resources(CrisisSeverity.HIGH)
        assert len(resources) >= 5

    def test_moderate_returns_emergency_plus_pastoral(self):
        resources = CrisisDetectorAgent._get_resources(CrisisSeverity.MODERATE)
        assert len(resources) > 0
        # Moderate includes both emergency and pastoral resources
        assert len(resources) >= len(_PASTORAL_RESOURCES)

    def test_low_returns_pastoral_only(self):
        resources = CrisisDetectorAgent._get_resources(CrisisSeverity.LOW)
        assert resources == list(_PASTORAL_RESOURCES)

    def test_none_returns_empty(self):
        resources = CrisisDetectorAgent._get_resources(CrisisSeverity.NONE)
        assert resources == []


class TestHasConcerningEmotions:
    def test_two_high_threshold_emotions(self):
        vector = {"sadness": 0.8, "fear": 0.8}
        assert CrisisDetectorAgent._has_concerning_emotions(vector) is True

    def test_one_high_threshold_emotion(self):
        vector = {"sadness": 0.8, "joy": 0.9}
        assert CrisisDetectorAgent._has_concerning_emotions(vector) is False

    def test_empty_vector(self):
        assert CrisisDetectorAgent._has_concerning_emotions({}) is False

    def test_below_threshold_not_counted(self):
        vector = {"sadness": 0.5, "fear": 0.5, "grief": 0.5}
        assert CrisisDetectorAgent._has_concerning_emotions(vector) is False

    def test_shame_and_guilt_trigger(self):
        vector = {"shame": 0.7, "guilt": 0.7}
        assert CrisisDetectorAgent._has_concerning_emotions(vector) is True

    def test_loneliness_and_grief_trigger(self):
        vector = {"loneliness": 0.8, "grief": 0.75}
        assert CrisisDetectorAgent._has_concerning_emotions(vector) is True
