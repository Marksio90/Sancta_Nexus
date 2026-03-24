"""Unit tests for PrayerGeneratorAgent (A-028)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.generative.prayer_generator import PrayerGeneratorAgent, _FALLBACK_PRAYER


SCRIPTURE_TEXT = "Ja jestem krzewem winnym, wy latoroślami."
EMOTION_STATE = "peace"


async def test_generate_returns_prayer_dict():
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "prayer_text": "Panie Jezu, trwam w Tobie jak latorośl w krzewie. Amen.",
        "tradition": "ignatian",
        "elements": ["colloquium", "petitio"],
    })

    with patch("app.agents.generative.prayer_generator.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)

        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE, tradition="ignatian")

    assert "prayer_text" in result
    assert "tradition" in result
    assert "elements" in result
    assert len(result["prayer_text"]) >= 30


async def test_generate_returns_fallback_on_short_response():
    mock_response = MagicMock()
    mock_response.content = json.dumps({"prayer_text": "Ok.", "tradition": "ignatian", "elements": []})

    with patch("app.agents.generative.prayer_generator.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)

        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE)

    assert result["prayer_text"] == _FALLBACK_PRAYER["prayer_text"]


async def test_generate_returns_fallback_on_llm_error():
    with patch("app.agents.generative.prayer_generator.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(side_effect=RuntimeError("timeout"))

        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE)

    assert "prayer_text" in result


@pytest.mark.parametrize("tradition", ["ignatian", "carmelite", "franciscan", "benedictine", "charismatic"])
async def test_generate_all_supported_traditions(tradition: str):
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "prayer_text": f"Modlitwa w tradycji {tradition}. " * 5,
        "tradition": tradition,
        "elements": ["laudatio"],
    })

    with patch("app.agents.generative.prayer_generator.ChatOpenAI") as MockLLM:
        instance = MockLLM.return_value
        instance.ainvoke = AsyncMock(return_value=mock_response)

        agent = PrayerGeneratorAgent()
        result = await agent.generate(SCRIPTURE_TEXT, EMOTION_STATE, tradition=tradition)

    assert result["tradition"] == tradition or result["tradition"] == "ignatian"


def test_prayer_generator_uses_settings_model():
    from app.core.config import settings
    with patch("app.agents.generative.prayer_generator.ChatOpenAI") as MockLLM:
        PrayerGeneratorAgent()
        call_kwargs = MockLLM.call_args
        used_model = call_kwargs.kwargs.get("model") or (call_kwargs.args[0] if call_kwargs.args else None)
        assert used_model == settings.LLM_CREATIVE_MODEL
