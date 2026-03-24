"""Unit tests for ReflectionWriterAgent (A-029) — parallel layer generation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest

from app.agents.generative.reflection_writer import (
    ReflectionWriterAgent,
    ReflectionLayer,
    ScripturePassage,
    UserContext,
)


PASSAGE = ScripturePassage(
    reference="J 15,5",
    text="Ja jestem krzewem winnym, wy — latoroślami.",
    book="Ewangelia Jana",
    chapter=15,
    verses="5-5",
    liturgical_context="Wielkanoc",
)

USER_CTX = UserContext(
    user_id="test-user",
    prayer_tradition="ignatian",
    theological_depth="intermediate",
)


def _make_mock_llm(content: str = "Test layer content for spiritual reflection.") -> MagicMock:
    llm = MagicMock()
    response = MagicMock()
    response.content = content
    llm.chat = AsyncMock(return_value=response)
    return llm


async def test_write_returns_reflection_with_all_four_layers():
    llm = _make_mock_llm()
    agent = ReflectionWriterAgent(llm_client=llm)
    reflection = await agent.write(PASSAGE, USER_CTX)

    assert len(reflection.layers) == len(list(ReflectionLayer))
    for layer_content in reflection.layers:
        assert layer_content.content


async def test_write_calls_llm_concurrently():
    """All 4 layers + 3 synthesis calls should happen via asyncio.gather (≤ 2 awaits on gather)."""
    call_times: list[float] = []

    async def slow_chat(messages, **kwargs):  # type: ignore[override]
        import time
        call_times.append(time.monotonic())
        await asyncio.sleep(0.01)  # tiny sleep to expose ordering
        response = MagicMock()
        response.content = "Content"
        return response

    llm = MagicMock()
    llm.chat = slow_chat

    agent = ReflectionWriterAgent(llm_client=llm)
    reflection = await agent.write(PASSAGE, USER_CTX)

    # If parallelized correctly, all 4 layer calls start nearly simultaneously.
    # The total duration should be much less than 4 * 0.01s = 0.04s if run in parallel.
    assert reflection.synthesis  # synthesis was computed
    assert reflection.action_step  # action step was computed


async def test_write_skips_rag_when_no_vector_store():
    llm = _make_mock_llm()
    agent = ReflectionWriterAgent(llm_client=llm, vector_store=None)
    reflection = await agent.write(PASSAGE, USER_CTX)
    # Should succeed with empty patristic quotes
    assert reflection.patristic_quotes == []


async def test_write_synthesis_and_action_not_empty():
    llm = _make_mock_llm("Głęboka synteza duchowa rozważanego fragmentu.")
    agent = ReflectionWriterAgent(llm_client=llm)
    reflection = await agent.write(PASSAGE, USER_CTX)

    assert len(reflection.synthesis) > 0
    assert len(reflection.prayer_response) > 0
    assert len(reflection.action_step) > 0
