"""Unit tests for app/agents/orchestration/orchestrator_supremus.py.

LangGraph is not installed; it is stubbed at sys.modules before import.
All tests exercise pure-logic constructs — no LLM, no DB.

Contracts verified:
- SanctaState TypedDict: known keys present
- VALID_INTENTS: exactly 6 intents, all expected values
- INTENT_ROUTING_PROMPT: format keys present
- _route_by_intent: known intent passes through, unknown → lectio_divina
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub langgraph BEFORE module import
if "langgraph" not in sys.modules:
    _sg = MagicMock()
    _sg.return_value = MagicMock()
    sys.modules["langgraph"] = MagicMock()
    sys.modules["langgraph.graph"] = MagicMock()
    sys.modules["langgraph.graph"].StateGraph = _sg
    sys.modules["langgraph.graph"].START = "__start__"
    sys.modules["langgraph.graph"].END = "__end__"

from app.agents.orchestration.orchestrator_supremus import (
    INTENT_ROUTING_PROMPT,
    VALID_INTENTS,
    OrchestratorSupremus,
    SanctaState,
)

# ---------------------------------------------------------------------------
# VALID_INTENTS
# ---------------------------------------------------------------------------


class TestValidIntents:
    def test_exactly_6_intents(self):
        assert len(VALID_INTENTS) == 6

    def test_lectio_divina(self):
        assert "lectio_divina" in VALID_INTENTS

    def test_free_reflection(self):
        assert "free_reflection" in VALID_INTENTS

    def test_interactive_bible(self):
        assert "interactive_bible" in VALID_INTENTS

    def test_spiritual_direction(self):
        assert "spiritual_direction" in VALID_INTENTS

    def test_community(self):
        assert "community" in VALID_INTENTS

    def test_crisis(self):
        assert "crisis" in VALID_INTENTS

    def test_is_frozenset(self):
        assert isinstance(VALID_INTENTS, frozenset)


# ---------------------------------------------------------------------------
# SanctaState TypedDict keys
# ---------------------------------------------------------------------------


class TestSanctaState:
    def test_required_keys_present(self):
        state = SanctaState(
            user_id="u-1",
            emotion_vector={"joy": 0.8},
            spiritual_state={},
            intent="lectio_divina",
        )
        assert state["user_id"] == "u-1"
        assert state["intent"] == "lectio_divina"

    def test_optional_keys(self):
        state = SanctaState(user_id="u-1")
        assert state.get("scripture") is None
        assert state.get("error") is None

    def test_all_stage_keys_defined(self):
        annotations = SanctaState.__annotations__
        for key in ("scripture", "meditation", "prayer", "contemplation", "action"):
            assert key in annotations


# ---------------------------------------------------------------------------
# INTENT_ROUTING_PROMPT
# ---------------------------------------------------------------------------


class TestIntentRoutingPrompt:
    def test_has_emotion_vector_placeholder(self):
        assert "{emotion_vector}" in INTENT_ROUTING_PROMPT

    def test_has_spiritual_state_placeholder(self):
        assert "{spiritual_state}" in INTENT_ROUTING_PROMPT

    def test_lists_all_valid_intents(self):
        for intent in VALID_INTENTS:
            assert intent in INTENT_ROUTING_PROMPT

    def test_not_empty(self):
        assert len(INTENT_ROUTING_PROMPT) > 100


# ---------------------------------------------------------------------------
# _route_by_intent
# ---------------------------------------------------------------------------


class TestRouteByIntent:
    def test_known_intent_passes_through(self):
        for intent in VALID_INTENTS:
            state = SanctaState(intent=intent)
            result = OrchestratorSupremus._route_by_intent(state)
            assert result == intent

    def test_unknown_intent_defaults_to_lectio_divina(self):
        state = SanctaState(intent="unknown_path")
        result = OrchestratorSupremus._route_by_intent(state)
        assert result == "lectio_divina"

    def test_missing_intent_defaults_to_lectio_divina(self):
        state = SanctaState()
        result = OrchestratorSupremus._route_by_intent(state)
        assert result == "lectio_divina"

    def test_crisis_routes_to_crisis(self):
        state = SanctaState(intent="crisis")
        assert OrchestratorSupremus._route_by_intent(state) == "crisis"

    def test_spiritual_direction_routes_correctly(self):
        state = SanctaState(intent="spiritual_direction")
        assert OrchestratorSupremus._route_by_intent(state) == "spiritual_direction"
