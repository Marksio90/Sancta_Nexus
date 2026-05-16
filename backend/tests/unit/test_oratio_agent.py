"""Unit tests for OratioAgent (A-012) — prayer generation with A-028 delegation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.lectio_divina.oratio_agent import FALLBACK_PRAYER, OratioAgent

SCRIPTURE = {
    "book": "Ewangelia Jana",
    "chapter": 15,
    "verse_start": 5,
    "verse_end": 5,
    "text": "Ja jestem krzewem winnym, wy — latoroślami.",
}
EMOTION_VECTOR = {"peace": 0.8, "gratitude": 0.5}


def _make_llm(response_content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=response_content))
    return llm


# ---------------------------------------------------------------------------
# Delegation to PrayerGeneratorAgent (A-028)
# Lazy-imported inside the method, so we patch the source class in its module.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tradition", ["ignatian", "carmelite", "franciscan", "benedictine", "charismatic"])
async def test_oratio_delegates_to_prayer_generator_for_supported_traditions(tradition: str):
    expected_prayer = {
        "prayer_text": "Panie Jezu, trwaj ze mną. Amen.",
        "tradition": tradition,
        "elements": ["colloquium"],
    }
    mock_llm = _make_llm('{"prayer_text": "Fallback.", "tradition": "ignatian", "elements": []}')

    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm), patch(
        "app.agents.generative.prayer_generator.PrayerGeneratorAgent",
        autospec=True,
    ) as MockAgent:
        instance = MockAgent.return_value
        instance.generate = AsyncMock(return_value=expected_prayer)

        agent = OratioAgent()
        result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition=tradition)

    assert result["prayer_text"] == expected_prayer["prayer_text"]
    instance.generate.assert_called_once()


async def test_oratio_falls_back_when_prayer_generator_raises():
    fallback_content = '{"prayer_text": "Fallback prayer text here.", "tradition": "ignatian", "elements": []}'
    mock_llm = _make_llm(fallback_content)

    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm), patch(
        "app.agents.generative.prayer_generator.PrayerGeneratorAgent",
        autospec=True,
    ) as MockAgent:
        instance = MockAgent.return_value
        instance.generate = AsyncMock(side_effect=RuntimeError("OpenAI down"))

        agent = OratioAgent()
        result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition="ignatian")

    assert "prayer_text" in result
    assert len(result["prayer_text"]) >= 10


# ---------------------------------------------------------------------------
# Dominican / Marian — no delegation, own LLM
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tradition", ["dominican", "marian"])
async def test_oratio_does_not_delegate_for_own_traditions(tradition: str):
    content = f'{{"prayer_text": "Przez Chrystusa Prawdę Wcieloną. Amen.", "tradition": "{tradition}", "elements": []}}'
    mock_llm = _make_llm(content)

    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm):
        with patch("app.agents.generative.prayer_generator.PrayerGeneratorAgent") as MockA028:
            agent = OratioAgent()
            await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition=tradition)
            MockA028.assert_not_called()


async def test_oratio_returns_fallback_when_llm_is_none():
    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", side_effect=Exception("no key")):
        agent = OratioAgent()
        result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition="ignatian")

    assert result["prayer_text"] == FALLBACK_PRAYER["prayer_text"]


async def test_oratio_normalizes_unknown_tradition():
    mock_llm = _make_llm('{"prayer_text": "Prayer.", "tradition": "ignatian", "elements": []}')
    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm):
        with patch("app.agents.generative.prayer_generator.PrayerGeneratorAgent") as MockA028:
            instance = MockA028.return_value
            instance.generate = AsyncMock(return_value={
                "prayer_text": "Prayer fallback.", "tradition": "ignatian", "elements": []
            })
            agent = OratioAgent()
            result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition="buddhist")

    assert "prayer_text" in result
