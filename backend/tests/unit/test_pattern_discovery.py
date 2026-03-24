"""Unit tests for PatternDiscoveryAgent (A-037)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.memory.pattern_discovery import PatternDiscoveryAgent, PATTERN_TYPES


SESSIONS = [
    {"date": "2026-01-01", "primary_emotion": "peace", "spiritual_state": "illumination", "scripture_ref": "J 15,5"},
    {"date": "2026-01-08", "primary_emotion": "gratitude", "spiritual_state": "consolation", "scripture_ref": "Ps 23"},
    {"date": "2026-01-15", "primary_emotion": "peace", "spiritual_state": "illumination", "scripture_ref": "J 15,5"},
]

LLM_RESPONSE = (
    "PATTERN: recurring_theme\nDESC: Zaufanie Bogu\nFREQ: tygodniowo\nSCRIPTURE: J 15,5, Ps 23\n"
    "PATTERN: grace_moment\nDESC: Głęboka modlitwa kontemplacyjna\nFREQ: raz w miesiącu\nSCRIPTURE: J 15,5"
)


async def test_discover_returns_pattern_list():
    mock_response = MagicMock()
    mock_response.content = LLM_RESPONSE

    with patch("app.agents.memory.pattern_discovery.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)

        agent = PatternDiscoveryAgent()
        patterns = await agent.discover("user-123", SESSIONS)

    assert isinstance(patterns, list)
    assert len(patterns) == 2
    assert patterns[0]["type"] == "recurring_theme"
    assert patterns[1]["type"] == "grace_moment"
    assert "description" in patterns[0]


async def test_discover_returns_defaults_when_no_sessions():
    with patch("app.agents.memory.pattern_discovery.ChatOpenAI"):
        agent = PatternDiscoveryAgent()
        patterns = await agent.discover("user-123", sessions=None)

    assert isinstance(patterns, list)
    assert len(patterns) >= 1
    assert "type" in patterns[0]


async def test_discover_returns_defaults_on_llm_error():
    with patch("app.agents.memory.pattern_discovery.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(side_effect=RuntimeError("timeout"))

        agent = PatternDiscoveryAgent()
        patterns = await agent.discover("user-123", SESSIONS)

    assert isinstance(patterns, list)
    assert len(patterns) >= 1


def test_pattern_discovery_uses_settings_model():
    from app.core.config import settings
    with patch("app.agents.memory.pattern_discovery.ChatOpenAI") as MockLLM:
        PatternDiscoveryAgent()
        call_kwargs = MockLLM.call_args
        used_model = (
            call_kwargs.kwargs.get("model")
            if call_kwargs.kwargs
            else (call_kwargs.args[0] if call_kwargs.args else None)
        )
        assert used_model == settings.LLM_FAST_MODEL
