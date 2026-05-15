"""Unit tests for app/agents/orchestration/quality_gate.py.

Self-contained — LLM is mocked. Instances are created by bypassing __init__
and injecting mocked dependencies directly.

Contracts verified:
- FALLBACK_CONTENT: all 5 stages present with required keys
- VALID_STAGES: matches FALLBACK_CONTENT keys
- MAX_RETRIES = 3, MIN_CONTENT_LENGTH = 20
- _CircuitState: record_failure, is_open, reset, failure_counts
- get_fallback_content: returns correct stage, unknown stage → scripture
- _extract_text: str passthrough, dict text key, prayer_text, guidance_text,
  challenge_text, list of questions
- _parse_json: valid JSON, JSON in prose, unparseable → safe default
- validate_output: valid content passes; too-short fails; theological fail
  records circuit; circuit open returns fallback immediately
- action stage skips theological check
- check_theological_safety: is_safe parsed from bool and str; LLM error → fail open
- validate(): whole state — failed stages replaced with fallback
"""

from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub app.core.llm so module-level import of get_llm_fast doesn't fail
# ---------------------------------------------------------------------------

_llm_stub = MagicMock()
_llm_stub.get_llm_fast = MagicMock(return_value=MagicMock())
if "app.core.llm" not in sys.modules:
    sys.modules["app.core.llm"] = _llm_stub

from app.agents.orchestration.quality_gate import (
    FALLBACK_CONTENT,
    MAX_RETRIES,
    MIN_CONTENT_LENGTH,
    VALID_STAGES,
    QualityGateAgent,
    _CircuitState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent(llm_json_response: dict | None = None, is_safe: bool = True) -> QualityGateAgent:
    """Build a QualityGateAgent with a mocked LLM that returns *llm_json_response*."""
    agent = QualityGateAgent.__new__(QualityGateAgent)
    agent._circuit = _CircuitState()

    if llm_json_response is None:
        llm_json_response = {"is_safe": is_safe, "confidence": 0.95, "concerns": []}

    mock_llm = MagicMock()
    llm_result = MagicMock()
    llm_result.content = json.dumps(llm_json_response)
    mock_llm.ainvoke = AsyncMock(return_value=llm_result)
    agent._llm = mock_llm

    return agent


def _long_text(n: int = 30) -> str:
    return "A" * n


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_retries_is_3(self):
        assert MAX_RETRIES == 3

    def test_min_content_length_is_20(self):
        assert MIN_CONTENT_LENGTH == 20

    def test_valid_stages_matches_fallback_content(self):
        assert VALID_STAGES == frozenset(FALLBACK_CONTENT.keys())


# ---------------------------------------------------------------------------
# FALLBACK_CONTENT structure
# ---------------------------------------------------------------------------


class TestFallbackContent:
    def test_has_all_five_stages(self):
        assert set(FALLBACK_CONTENT.keys()) == {
            "scripture", "meditation", "prayer", "contemplation", "action"
        }

    def test_scripture_has_text(self):
        assert "text" in FALLBACK_CONTENT["scripture"]
        assert len(FALLBACK_CONTENT["scripture"]["text"]) > 20

    def test_prayer_has_prayer_text(self):
        assert "prayer_text" in FALLBACK_CONTENT["prayer"]

    def test_contemplation_has_guidance_text(self):
        assert "guidance_text" in FALLBACK_CONTENT["contemplation"]

    def test_action_has_challenge_text(self):
        assert "challenge_text" in FALLBACK_CONTENT["action"]

    def test_meditation_has_questions(self):
        assert "questions" in FALLBACK_CONTENT["meditation"]
        assert isinstance(FALLBACK_CONTENT["meditation"]["questions"], list)


# ---------------------------------------------------------------------------
# _CircuitState
# ---------------------------------------------------------------------------


class TestCircuitState:
    def test_initial_not_open(self):
        cs = _CircuitState()
        assert cs.is_open("node-1") is False

    def test_record_failure_increments(self):
        cs = _CircuitState()
        cs.record_failure("node-1")
        assert cs.failures["node-1"] == 1

    def test_open_after_max_retries(self):
        cs = _CircuitState()
        for _ in range(MAX_RETRIES):
            cs.record_failure("node-1")
        assert cs.is_open("node-1") is True

    def test_not_open_before_max_retries(self):
        cs = _CircuitState()
        for _ in range(MAX_RETRIES - 1):
            cs.record_failure("node-1")
        assert cs.is_open("node-1") is False

    def test_reset_clears_failures(self):
        cs = _CircuitState()
        for _ in range(MAX_RETRIES):
            cs.record_failure("node-1")
        cs.reset("node-1")
        assert cs.is_open("node-1") is False
        assert cs.failures.get("node-1", 0) == 0

    def test_reset_unknown_node_is_noop(self):
        cs = _CircuitState()
        cs.reset("nonexistent")  # should not raise

    def test_failure_counts_returns_dict(self):
        cs = _CircuitState()
        cs.record_failure("node-a")
        cs.record_failure("node-a")
        cs.record_failure("node-b")
        counts = cs.failure_counts
        assert counts == {"node-a": 2, "node-b": 1}

    def test_different_nodes_independent(self):
        cs = _CircuitState()
        for _ in range(MAX_RETRIES):
            cs.record_failure("node-1")
        assert cs.is_open("node-1") is True
        assert cs.is_open("node-2") is False


# ---------------------------------------------------------------------------
# get_fallback_content
# ---------------------------------------------------------------------------


class TestGetFallbackContent:
    def test_returns_scripture_fallback(self):
        agent = _agent()
        fb = agent.get_fallback_content("scripture")
        assert "text" in fb

    def test_returns_prayer_fallback(self):
        agent = _agent()
        fb = agent.get_fallback_content("prayer")
        assert "prayer_text" in fb

    def test_unknown_stage_returns_scripture(self):
        agent = _agent()
        fb = agent.get_fallback_content("totally_unknown_stage")
        assert "text" in fb  # scripture fallback

    def test_returns_copy_not_original(self):
        agent = _agent()
        fb = agent.get_fallback_content("action")
        fb["extra_key"] = "injected"
        assert "extra_key" not in FALLBACK_CONTENT["action"]


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_string_passthrough(self):
        result = QualityGateAgent._extract_text("direct text")
        assert result == "direct text"

    def test_dict_text_key(self):
        result = QualityGateAgent._extract_text({"text": "scripture content"})
        assert result == "scripture content"

    def test_dict_prayer_text_key(self):
        result = QualityGateAgent._extract_text({"prayer_text": "O Lord..."})
        assert result == "O Lord..."

    def test_dict_guidance_text_key(self):
        result = QualityGateAgent._extract_text({"guidance_text": "Breathe..."})
        assert result == "Breathe..."

    def test_dict_challenge_text_key(self):
        result = QualityGateAgent._extract_text({"challenge_text": "Do this..."})
        assert result == "Do this..."

    def test_dict_questions_as_list(self):
        result = QualityGateAgent._extract_text({"questions": ["Q1?", "Q2?"]})
        assert "Q1?" in result and "Q2?" in result

    def test_fallback_to_str_repr(self):
        result = QualityGateAgent._extract_text({"unknown_key": "value"})
        # Falls back to str(content)
        assert "unknown_key" in result or "value" in result


# ---------------------------------------------------------------------------
# _parse_json
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_valid_json(self):
        raw = '{"is_safe": true, "confidence": 0.9}'
        result = QualityGateAgent._parse_json(raw)
        assert result["is_safe"] is True
        assert result["confidence"] == 0.9

    def test_json_in_prose(self):
        raw = 'The result is: {"is_safe": false, "concerns": ["heresy"]} as stated.'
        result = QualityGateAgent._parse_json(raw)
        assert result["is_safe"] is False

    def test_unparseable_returns_safe_default(self):
        result = QualityGateAgent._parse_json("This is not JSON at all.")
        assert result.get("is_safe") is True

    def test_empty_json(self):
        result = QualityGateAgent._parse_json("{}")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# validate_output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidateOutput:
    async def test_valid_content_passes(self):
        agent = _agent(is_safe=True)
        content = {"text": "A" * 30}
        result = await agent.validate_output("scripture", content, {})
        assert result["is_valid"] is True
        assert result["used_fallback"] is False
        assert result["stage"] == "scripture"

    async def test_short_content_fails(self):
        agent = _agent()
        content = {"text": "short"}
        result = await agent.validate_output("scripture", content, {})
        assert result["is_valid"] is False
        assert "too short" in result["concerns"][0].lower()

    async def test_short_content_records_circuit_failure(self):
        agent = _agent()
        content = {"text": "x"}
        await agent.validate_output("scripture", content, {})
        assert agent._circuit.failures.get("quality_gate.scripture", 0) == 1

    async def test_theological_fail_records_failure(self):
        agent = _agent({"is_safe": False, "confidence": 0.1, "concerns": ["heresy"]})
        content = {"text": "A" * 30}
        result = await agent.validate_output("scripture", content, {})
        assert result["is_valid"] is False
        assert "heresy" in result["concerns"]

    async def test_circuit_open_returns_fallback_immediately(self):
        agent = _agent(is_safe=True)
        # Trip the circuit
        for _ in range(MAX_RETRIES):
            agent._circuit.record_failure("quality_gate.scripture")
        content = {"text": "A" * 30}
        result = await agent.validate_output("scripture", content, {})
        assert result["is_valid"] is False
        assert result["used_fallback"] is True
        assert "circuit_breaker_open" in result["concerns"]

    async def test_action_stage_skips_theological_check(self):
        agent = _agent(is_safe=False)  # LLM would say unsafe — but should be skipped
        content = {"challenge_text": "A" * 30}
        result = await agent.validate_output("action", content, {})
        assert result["is_valid"] is True
        agent._llm.ainvoke.assert_not_awaited()

    async def test_success_resets_circuit(self):
        agent = _agent(is_safe=True)
        # Add one failure first
        agent._circuit.record_failure("quality_gate.meditation")
        content = {"questions": ["Long enough question for testing purposes here?"]}
        await agent.validate_output("meditation", content, {})
        # After success, failures should be cleared
        assert agent._circuit.failures.get("quality_gate.meditation", 0) == 0

    async def test_returns_required_keys(self):
        agent = _agent()
        result = await agent.validate_output("prayer", {"prayer_text": "A" * 30}, {})
        assert {"is_valid", "stage", "content", "concerns", "used_fallback"} <= set(result.keys())

    async def test_nth_failure_triggers_fallback(self):
        """The MAX_RETRIES-th short-content failure should return fallback."""
        agent = _agent()
        # Pre-load 2 failures (one short of MAX_RETRIES)
        for _ in range(MAX_RETRIES - 1):
            agent._circuit.record_failure("quality_gate.scripture")
        # This call should push it to MAX_RETRIES and return fallback
        result = await agent.validate_output("scripture", {"text": "x"}, {})
        assert result["used_fallback"] is True


# ---------------------------------------------------------------------------
# check_theological_safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCheckTheologicalSafety:
    async def test_returns_safe_for_safe_content(self):
        agent = _agent({"is_safe": True, "confidence": 0.95, "concerns": []})
        result = await agent.check_theological_safety("Orthodox Catholic content")
        assert result["is_safe"] is True
        assert result["confidence"] == 0.95

    async def test_returns_unsafe_for_heretical_content(self):
        agent = _agent({
            "is_safe": False, "confidence": 0.85, "concerns": ["Pelagianism detected"]
        })
        result = await agent.check_theological_safety("heretical text")
        assert result["is_safe"] is False
        assert "Pelagianism detected" in result["concerns"]

    async def test_is_safe_string_true_parsed(self):
        agent = _agent({"is_safe": "true", "confidence": 0.9, "concerns": []})
        result = await agent.check_theological_safety("text")
        assert result["is_safe"] is True

    async def test_is_safe_string_false_parsed(self):
        agent = _agent({"is_safe": "false", "confidence": 0.9, "concerns": []})
        result = await agent.check_theological_safety("text")
        assert result["is_safe"] is False

    async def test_llm_error_fails_open(self):
        agent = _agent()
        agent._llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await agent.check_theological_safety("text")
        assert result["is_safe"] is True  # fail open
        assert len(result["concerns"]) > 0

    async def test_has_all_required_keys(self):
        agent = _agent()
        result = await agent.check_theological_safety("text")
        assert {"is_safe", "confidence", "concerns", "suggestion"} <= set(result.keys())


# ---------------------------------------------------------------------------
# validate() — full state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidateState:
    async def test_passes_through_valid_state(self):
        agent = _agent(is_safe=True)
        state = {
            "prayer": {"prayer_text": "A" * 30},
            "action": {"challenge_text": "B" * 30},
        }
        result = await agent.validate(state)
        assert result["prayer"]["prayer_text"] == "A" * 30

    async def test_adds_theological_validation_key(self):
        agent = _agent(is_safe=True)
        result = await agent.validate({"action": {"challenge_text": "A" * 30}})
        assert "theological_validation" in result
        assert result["theological_validation"]["status"] == "passed"

    async def test_replaces_failed_stage_with_fallback(self):
        agent = _agent({"is_safe": False, "confidence": 0.1, "concerns": ["bad"]})
        # Trip circuit so it returns fallback on next call
        for _ in range(MAX_RETRIES):
            agent._circuit.record_failure("quality_gate.scripture")
        state = {"scripture": {"text": "short"}}
        result = await agent.validate(state)
        # Scripture should be replaced with fallback (Psalm 23)
        assert "Pan" in result["scripture"].get("text", "")

    async def test_empty_stages_skipped(self):
        agent = _agent(is_safe=True)
        result = await agent.validate({"scripture": None, "prayer": None})
        assert "theological_validation" in result

    async def test_check_circuit_breaker(self):
        agent = _agent()
        for _ in range(MAX_RETRIES):
            agent._circuit.record_failure("quality_gate.meditation")
        assert agent.check_circuit_breaker("meditation") is True

    async def test_failure_counts_property(self):
        agent = _agent()
        agent._circuit.record_failure("quality_gate.prayer")
        counts = agent.failure_counts
        assert counts.get("quality_gate.prayer", 0) == 1
