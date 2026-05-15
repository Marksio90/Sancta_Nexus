"""Unit tests for LLMClientAdapter (app/core/llm.py).

No real LLM calls — mock the underlying BaseChatModel.

Contracts verified:
LLMClientAdapter:
- Stores the LLM under self._llm
- chat() converts system role → SystemMessage
- chat() converts user/default role → HumanMessage
- chat() converts assistant role → AIMessage
- chat() passes all messages to llm.ainvoke
- Returns the result from ainvoke unchanged
- Passes temperature override via bind()
- Passes max_tokens override via bind()
- No overrides → bind() not called
- bind() failure silently ignored, ainvoke still called
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_adapter():
    from app.core.llm import LLMClientAdapter
    mock_llm = MagicMock()
    response = MagicMock()
    response.content = "Boże, bądź uwielbiony."
    mock_llm.ainvoke = AsyncMock(return_value=response)
    mock_llm.bind = MagicMock(return_value=mock_llm)
    return LLMClientAdapter(mock_llm), mock_llm, response


class TestLLMClientAdapterInit:
    def test_stores_llm(self):
        from app.core.llm import LLMClientAdapter
        mock = MagicMock()
        adapter = LLMClientAdapter(mock)
        assert adapter._llm is mock


class TestLLMClientAdapterChat:
    @pytest.mark.asyncio
    async def test_system_message_converted(self):
        from langchain_core.messages import SystemMessage
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "system", "content": "Jesteś asystentem."}])
        called = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(called[0], SystemMessage)
        assert called[0].content == "Jesteś asystentem."

    @pytest.mark.asyncio
    async def test_user_message_converted_to_human(self):
        from langchain_core.messages import HumanMessage
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "user", "content": "Mam pytanie."}])
        called = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(called[0], HumanMessage)

    @pytest.mark.asyncio
    async def test_default_role_is_human(self):
        from langchain_core.messages import HumanMessage
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"content": "Bez roli."}])
        called = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(called[0], HumanMessage)

    @pytest.mark.asyncio
    async def test_assistant_message_converted_to_ai(self):
        from langchain_core.messages import AIMessage
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "assistant", "content": "Odpowiem."}])
        called = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(called[0], AIMessage)

    @pytest.mark.asyncio
    async def test_multiple_messages_converted(self):
        from langchain_core.messages import HumanMessage, SystemMessage
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([
            {"role": "system", "content": "System."},
            {"role": "user", "content": "Użytkownik."},
        ])
        called = mock_llm.ainvoke.call_args[0][0]
        assert len(called) == 2
        assert isinstance(called[0], SystemMessage)
        assert isinstance(called[1], HumanMessage)

    @pytest.mark.asyncio
    async def test_returns_ainvoke_result(self):
        adapter, mock_llm, response = _make_adapter()
        result = await adapter.chat([{"role": "user", "content": "test"}])
        assert result is response

    @pytest.mark.asyncio
    async def test_temperature_override_calls_bind(self):
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "user", "content": "test"}], temperature=0.9)
        mock_llm.bind.assert_called_once()
        call_kwargs = mock_llm.bind.call_args[1]
        assert call_kwargs.get("temperature") == 0.9

    @pytest.mark.asyncio
    async def test_max_tokens_override_calls_bind(self):
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "user", "content": "test"}], max_tokens=512)
        mock_llm.bind.assert_called_once()
        call_kwargs = mock_llm.bind.call_args[1]
        assert call_kwargs.get("max_tokens") == 512

    @pytest.mark.asyncio
    async def test_no_overrides_bind_not_called(self):
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "user", "content": "test"}])
        mock_llm.bind.assert_not_called()

    @pytest.mark.asyncio
    async def test_bind_failure_silently_ignored(self):
        from app.core.llm import LLMClientAdapter
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = "OK"
        mock_llm.ainvoke = AsyncMock(return_value=response)
        mock_llm.bind = MagicMock(side_effect=AttributeError("no bind"))
        adapter = LLMClientAdapter(mock_llm)
        result = await adapter.chat(
            [{"role": "user", "content": "test"}],
            temperature=0.5,
        )
        assert result is response

    @pytest.mark.asyncio
    async def test_empty_messages_list(self):
        adapter, mock_llm, response = _make_adapter()
        result = await adapter.chat([])
        mock_llm.ainvoke.assert_called_once()
        assert result is response

    @pytest.mark.asyncio
    async def test_content_preserved(self):
        from langchain_core.messages import HumanMessage
        adapter, mock_llm, _ = _make_adapter()
        await adapter.chat([{"role": "user", "content": "Specjalny znak: ąęółż"}])
        called = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(called[0], HumanMessage)
        assert "ąęółż" in called[0].content
