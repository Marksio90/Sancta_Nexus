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


def _make_llm(response_content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=response_content))
    return llm


async def test_discover_returns_pattern_list():
    mock_llm = _make_llm(LLM_RESPONSE)
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm):
        agent = PatternDiscoveryAgent()
        patterns = await agent.discover("user-123", SESSIONS)

    assert isinstance(patterns, list)
    assert len(patterns) == 2
    assert patterns[0]["type"] == "recurring_theme"
    assert patterns[1]["type"] == "grace_moment"
    assert "description" in patterns[0]


async def test_discover_returns_defaults_when_no_sessions():
    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm):
        agent = PatternDiscoveryAgent()
        patterns = await agent.discover("user-123", sessions=None)

    assert isinstance(patterns, list)
    assert len(patterns) >= 1
    assert "type" in patterns[0]


async def test_discover_returns_defaults_on_llm_error():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("timeout"))
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm):
        agent = PatternDiscoveryAgent()
        patterns = await agent.discover("user-123", SESSIONS)

    assert isinstance(patterns, list)
    assert len(patterns) >= 1


def test_pattern_discovery_uses_llm_factory():
    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm_fast", return_value=mock_llm) as mock_factory:
        PatternDiscoveryAgent()
        mock_factory.assert_called_once()
