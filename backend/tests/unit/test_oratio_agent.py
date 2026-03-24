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


# ---------------------------------------------------------------------------
# Delegation to PrayerGeneratorAgent (A-028)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tradition", ["ignatian", "carmelite", "franciscan", "benedictine", "charismatic"])
async def test_oratio_delegates_to_prayer_generator_for_supported_traditions(tradition: str):
    """For the 5 traditions supported by A-028, OratioAgent should delegate."""
    expected_prayer = {
        "prayer_text": "Panie Jezu, trwaj ze mną. Amen.",
        "tradition": tradition,
        "elements": ["colloquium"],
    }

    with patch(
        "app.agents.lectio_divina.oratio_agent.PrayerGeneratorAgent",
        autospec=True,
    ) as MockAgent:
        instance = MockAgent.return_value
        instance.generate = AsyncMock(return_value=expected_prayer)

        # Patch get_llm_creative to avoid OpenAI init
        with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative"):
            agent = OratioAgent()
            result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition=tradition)

    assert result["prayer_text"] == expected_prayer["prayer_text"]
    instance.generate.assert_called_once()


async def test_oratio_falls_back_when_prayer_generator_raises():
    """If A-028 fails, OratioAgent should use its own LLM template."""
    with patch(
        "app.agents.lectio_divina.oratio_agent.PrayerGeneratorAgent",
        autospec=True,
    ) as MockAgent:
        instance = MockAgent.return_value
        instance.generate = AsyncMock(side_effect=RuntimeError("OpenAI down"))

        # Also mock the agent's own LLM to return a valid prayer
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"prayer_text": "Fallback prayer text here.", "tradition": "ignatian", "elements": []}'
            )
        )
        with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm):
            agent = OratioAgent()
            result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition="ignatian")

    assert "prayer_text" in result
    assert len(result["prayer_text"]) >= 10


# ---------------------------------------------------------------------------
# Dominican / Marian — no delegation, own LLM
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tradition", ["dominican", "marian"])
async def test_oratio_does_not_delegate_for_own_traditions(tradition: str):
    """Dominican and Marian are OratioAgent-only — PrayerGeneratorAgent must NOT be called."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content='{"prayer_text": "Przez Chrystusa Prawdę Wcieloną. Amen.", "tradition": "' + tradition + '", "elements": []}'
        )
    )

    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm):
        with patch("app.agents.lectio_divina.oratio_agent.PrayerGeneratorAgent") as MockA028:
            agent = OratioAgent()
            await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition=tradition)
            MockA028.assert_not_called()


# ---------------------------------------------------------------------------
# Fallback when LLM is None
# ---------------------------------------------------------------------------

async def test_oratio_returns_fallback_when_llm_is_none():
    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", side_effect=Exception("no key")):
        agent = OratioAgent()
        result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition="ignatian")

    assert result["prayer_text"] == FALLBACK_PRAYER["prayer_text"]


# ---------------------------------------------------------------------------
# Unknown tradition → normalize to ignatian
# ---------------------------------------------------------------------------

async def test_oratio_normalizes_unknown_tradition():
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=MagicMock(content='{"prayer_text": "Prayer.", "tradition": "ignatian", "elements": []}')
    )
    with patch("app.agents.lectio_divina.oratio_agent.get_llm_creative", return_value=mock_llm):
        agent = OratioAgent()
        # Patch PrayerGeneratorAgent to avoid real API call
        with patch("app.agents.lectio_divina.oratio_agent.PrayerGeneratorAgent") as MockA028:
            instance = MockA028.return_value
            instance.generate = AsyncMock(return_value={"prayer_text": "Prayer fallback.", "tradition": "ignatian", "elements": []})
            result = await agent.pray(SCRIPTURE, EMOTION_VECTOR, tradition="buddhist")

    # Should not crash and should return something
    assert "prayer_text" in result
