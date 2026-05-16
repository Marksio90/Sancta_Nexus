"""Unit tests for PrayerGeneratorAgent (A-028)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.generative.prayer_generator import _FALLBACK_PRAYER, PrayerGeneratorAgent

SCRIPTURE_TEXT = "Ja jestem krzewem winnym, wy latoroślami."
EMOTION_STATE = "peace"


def _make_llm(response_content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=response_content))
    return llm


async def test_generate_returns_prayer_dict():
    mock_llm = _make_llm(json.dumps({
        "prayer_text": "Panie Jezu, trwam w Tobie jak latorośl w krzewie. Amen.",
        "tradition": "ignatian",
        "elements": ["colloquium", "petitio"],
    }))
    with patch("app.core.llm.get_llm", return_value=mock_llm):
        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE, tradition="ignatian")

    assert "prayer_text" in result
    assert "tradition" in result
    assert "elements" in result
    assert len(result["prayer_text"]) >= 30


async def test_generate_returns_fallback_on_short_response():
    mock_llm = _make_llm(json.dumps({"prayer_text": "Ok.", "tradition": "ignatian", "elements": []}))
    with patch("app.core.llm.get_llm", return_value=mock_llm):
        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE)

    assert result["prayer_text"] == _FALLBACK_PRAYER["prayer_text"]


async def test_generate_returns_fallback_on_llm_error():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("timeout"))
    with patch("app.core.llm.get_llm", return_value=mock_llm):
        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE)

    assert "prayer_text" in result


@pytest.mark.parametrize("tradition", ["ignatian", "carmelite", "franciscan", "benedictine", "charismatic"])
async def test_generate_all_supported_traditions(tradition: str):
    mock_llm = _make_llm(json.dumps({
        "prayer_text": f"Modlitwa w tradycji {tradition}. " * 5,
        "tradition": tradition,
        "elements": ["laudatio"],
    }))
    with patch("app.core.llm.get_llm", return_value=mock_llm):
        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE, tradition=tradition)

    assert result["tradition"] == tradition or result["tradition"] == "ignatian"


def test_prayer_generator_uses_llm_factory():
    mock_llm = MagicMock()
    with patch("app.core.llm.get_llm", return_value=mock_llm) as mock_factory:
        PrayerGeneratorAgent()
        mock_factory.assert_called_once()
