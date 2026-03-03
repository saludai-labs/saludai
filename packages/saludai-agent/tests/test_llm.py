"""Tests for saludai_agent.llm — message conversion and factory."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from saludai_agent.config import AgentConfig
from saludai_agent.exceptions import LLMResponseError
from saludai_agent.llm import (
    _anthropic_response_to_llm_response,
    _messages_to_anthropic,
    _messages_to_openai,
    _openai_response_to_llm_response,
    _tools_to_openai,
    create_llm_client,
)
from saludai_agent.types import Message, ToolCall

# ---------------------------------------------------------------------------
# Anthropic message conversion
# ---------------------------------------------------------------------------


class TestMessagesToAnthropic:
    """Convert provider-agnostic messages to Anthropic API format."""

    def test_user_message(self) -> None:
        messages = [Message(role="user", content="hello")]
        result = _messages_to_anthropic(messages)
        assert result == [{"role": "user", "content": "hello"}]

    def test_system_messages_are_skipped(self) -> None:
        messages = [Message(role="system", content="system prompt")]
        result = _messages_to_anthropic(messages)
        assert result == []

    def test_assistant_with_text(self) -> None:
        messages = [Message(role="assistant", content="response")]
        result = _messages_to_anthropic(messages)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == [{"type": "text", "text": "response"}]

    def test_assistant_with_tool_call(self) -> None:
        tc = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "diabetes"})
        messages = [Message(role="assistant", tool_calls=(tc,))]
        result = _messages_to_anthropic(messages)
        assert len(result) == 1
        content = result[0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "tool_use"
        assert content[0]["id"] == "tc_1"
        assert content[0]["name"] == "resolve_terminology"
        assert content[0]["input"] == {"term": "diabetes"}

    def test_assistant_with_text_and_tool_call(self) -> None:
        tc = ToolCall(id="tc_1", name="test", arguments={})
        messages = [Message(role="assistant", content="thinking...", tool_calls=(tc,))]
        result = _messages_to_anthropic(messages)
        content = result[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "tool_use"

    def test_tool_result_message(self) -> None:
        messages = [Message(role="tool", content='{"code": "123"}', tool_call_id="tc_1")]
        result = _messages_to_anthropic(messages)
        assert result[0]["role"] == "user"
        assert result[0]["content"][0]["type"] == "tool_result"
        assert result[0]["content"][0]["tool_use_id"] == "tc_1"

    def test_full_conversation(self) -> None:
        tc = ToolCall(id="tc_1", name="test", arguments={"x": 1})
        messages = [
            Message(role="user", content="find patients"),
            Message(role="assistant", tool_calls=(tc,)),
            Message(role="tool", content="found 5", tool_call_id="tc_1"),
            Message(role="assistant", content="There are 5 patients."),
        ]
        result = _messages_to_anthropic(messages)
        assert len(result) == 4
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"  # tool result wrapped as user
        assert result[3]["role"] == "assistant"


# ---------------------------------------------------------------------------
# Anthropic response conversion
# ---------------------------------------------------------------------------


class TestAnthropicResponseConversion:
    """Convert Anthropic API responses to LLMResponse."""

    def test_text_response(self) -> None:
        response = MagicMock()
        response.content = [MagicMock(type="text", text="Hello world")]
        response.stop_reason = "end_turn"
        response.usage = MagicMock(input_tokens=10, output_tokens=5)

        result = _anthropic_response_to_llm_response(response)
        assert result.content == "Hello world"
        assert result.tool_calls == ()
        assert result.stop_reason == "end_turn"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5

    def test_tool_use_response(self) -> None:
        tool_block = MagicMock(type="tool_use", id="toolu_123", input={"term": "diabetes"})
        tool_block.name = "resolve_terminology"
        response = MagicMock()
        response.content = [tool_block]
        response.stop_reason = "tool_use"
        response.usage = MagicMock(input_tokens=20, output_tokens=10)

        result = _anthropic_response_to_llm_response(response)
        assert result.content is None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "toolu_123"
        assert result.tool_calls[0].name == "resolve_terminology"
        assert result.tool_calls[0].arguments == {"term": "diabetes"}

    def test_mixed_text_and_tool(self) -> None:
        text_block = MagicMock(type="text", text="Let me search...")
        tool_block = MagicMock(
            type="tool_use",
            id="toolu_456",
            name="search_fhir",
            input={"resource_type": "Patient"},
        )
        response = MagicMock()
        response.content = [text_block, tool_block]
        response.stop_reason = "tool_use"
        response.usage = MagicMock(input_tokens=30, output_tokens=15)

        result = _anthropic_response_to_llm_response(response)
        assert result.content == "Let me search..."
        assert len(result.tool_calls) == 1


# ---------------------------------------------------------------------------
# OpenAI message conversion
# ---------------------------------------------------------------------------


class TestMessagesToOpenAI:
    """Convert provider-agnostic messages to OpenAI chat format."""

    def test_system_prompt_prepended(self) -> None:
        messages = [Message(role="user", content="hi")]
        result = _messages_to_openai("system prompt", messages)
        assert result[0] == {"role": "system", "content": "system prompt"}
        assert result[1] == {"role": "user", "content": "hi"}

    def test_system_messages_in_list_are_skipped(self) -> None:
        messages = [
            Message(role="system", content="ignored"),
            Message(role="user", content="hi"),
        ]
        result = _messages_to_openai("real system", messages)
        assert len(result) == 2  # system from param + user

    def test_assistant_with_tool_calls(self) -> None:
        tc = ToolCall(id="call_1", name="test", arguments={"x": 1})
        messages = [Message(role="assistant", content="thinking", tool_calls=(tc,))]
        result = _messages_to_openai("sys", messages)
        assistant_msg = result[1]
        assert assistant_msg["content"] == "thinking"
        assert len(assistant_msg["tool_calls"]) == 1
        func = assistant_msg["tool_calls"][0]
        assert func["id"] == "call_1"
        assert func["type"] == "function"
        assert func["function"]["name"] == "test"
        assert json.loads(func["function"]["arguments"]) == {"x": 1}

    def test_tool_result(self) -> None:
        messages = [Message(role="tool", content="result", tool_call_id="call_1")]
        result = _messages_to_openai("sys", messages)
        tool_msg = result[1]
        assert tool_msg["role"] == "tool"
        assert tool_msg["tool_call_id"] == "call_1"
        assert tool_msg["content"] == "result"


class TestToolsToOpenAI:
    """Convert Anthropic-style tool defs to OpenAI function calling format."""

    def test_conversion(self) -> None:
        tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "input_schema": {
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                },
            }
        ]
        result = _tools_to_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "test_tool"
        assert result[0]["function"]["description"] == "A test tool"
        assert "properties" in result[0]["function"]["parameters"]


# ---------------------------------------------------------------------------
# OpenAI response conversion
# ---------------------------------------------------------------------------


class TestOpenAIResponseConversion:
    """Convert OpenAI API responses to LLMResponse."""

    def test_text_response(self) -> None:
        message = MagicMock()
        message.content = "Hello"
        message.tool_calls = None
        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "stop"
        response = MagicMock()
        response.choices = [choice]
        response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        result = _openai_response_to_llm_response(response)
        assert result.content == "Hello"
        assert result.tool_calls == ()
        assert result.stop_reason == "stop"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5

    def test_tool_call_response(self) -> None:
        func = MagicMock()
        func.name = "resolve_terminology"
        func.arguments = '{"term": "diabetes"}'
        tc = MagicMock()
        tc.id = "call_123"
        tc.function = func

        message = MagicMock()
        message.content = None
        message.tool_calls = [tc]
        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "tool_calls"
        response = MagicMock()
        response.choices = [choice]
        response.usage = MagicMock(prompt_tokens=20, completion_tokens=10)

        result = _openai_response_to_llm_response(response)
        assert result.content is None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call_123"
        assert result.tool_calls[0].name == "resolve_terminology"
        assert result.tool_calls[0].arguments == {"term": "diabetes"}

    def test_invalid_json_in_tool_args_raises(self) -> None:
        func = MagicMock()
        func.name = "test"
        func.arguments = "not json"
        tc = MagicMock()
        tc.id = "call_1"
        tc.function = func

        message = MagicMock()
        message.content = None
        message.tool_calls = [tc]
        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "tool_calls"
        response = MagicMock()
        response.choices = [choice]
        response.usage = None

        with pytest.raises(LLMResponseError, match="Failed to parse"):
            _openai_response_to_llm_response(response)

    def test_no_usage_defaults_to_zero(self) -> None:
        message = MagicMock()
        message.content = "ok"
        message.tool_calls = None
        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "stop"
        response = MagicMock()
        response.choices = [choice]
        response.usage = None

        result = _openai_response_to_llm_response(response)
        assert result.usage.input_tokens == 0
        assert result.usage.output_tokens == 0


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


class TestCreateLLMClient:
    """create_llm_client produces the right client type."""

    @patch("saludai_agent.llm.AnthropicLLMClient")
    def test_anthropic_provider(self, mock_cls: MagicMock) -> None:
        config = AgentConfig(llm_provider="anthropic", llm_model="claude-test")
        create_llm_client(config)
        mock_cls.assert_called_once_with(model="claude-test", api_key=None)

    @patch("saludai_agent.llm.OpenAILLMClient")
    def test_openai_provider(self, mock_cls: MagicMock) -> None:
        config = AgentConfig(llm_provider="openai", llm_model="gpt-4o", llm_api_key="sk-test")
        create_llm_client(config)
        mock_cls.assert_called_once_with(model="gpt-4o", api_key="sk-test", base_url=None)

    @patch("saludai_agent.llm.OpenAILLMClient")
    def test_ollama_provider_defaults(self, mock_cls: MagicMock) -> None:
        config = AgentConfig(llm_provider="ollama", llm_model="llama3")
        create_llm_client(config)
        mock_cls.assert_called_once_with(
            model="llama3",
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )

    @patch("saludai_agent.llm.OpenAILLMClient")
    def test_ollama_with_custom_url(self, mock_cls: MagicMock) -> None:
        config = AgentConfig(
            llm_provider="ollama",
            llm_model="llama3",
            llm_base_url="http://remote:11434/v1",
        )
        create_llm_client(config)
        mock_cls.assert_called_once_with(
            model="llama3",
            api_key="ollama",
            base_url="http://remote:11434/v1",
        )
