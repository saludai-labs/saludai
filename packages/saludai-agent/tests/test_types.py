"""Tests for saludai_agent.types."""

from __future__ import annotations

import pytest

from saludai_agent.types import (
    AgentResult,
    LLMResponse,
    Message,
    TokenUsage,
    ToolCall,
    ToolResult,
)


class TestToolCall:
    """ToolCall is frozen and stores tool invocation data."""

    def test_creation(self) -> None:
        tc = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "diabetes"})
        assert tc.id == "tc_1"
        assert tc.name == "resolve_terminology"
        assert tc.arguments == {"term": "diabetes"}

    def test_frozen(self) -> None:
        tc = ToolCall(id="tc_1", name="test", arguments={})
        with pytest.raises(AttributeError):
            tc.name = "other"  # type: ignore[misc]


class TestToolResult:
    """ToolResult stores tool execution output."""

    def test_creation(self) -> None:
        tr = ToolResult(tool_call_id="tc_1", content="result text")
        assert tr.tool_call_id == "tc_1"
        assert tr.content == "result text"
        assert tr.is_error is False

    def test_error_result(self) -> None:
        tr = ToolResult(tool_call_id="tc_1", content="error msg", is_error=True)
        assert tr.is_error is True

    def test_frozen(self) -> None:
        tr = ToolResult(tool_call_id="tc_1", content="ok")
        with pytest.raises(AttributeError):
            tr.content = "changed"  # type: ignore[misc]


class TestMessage:
    """Message stores conversation entries."""

    def test_user_message(self) -> None:
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.tool_calls == ()
        assert msg.tool_call_id is None

    def test_assistant_with_tool_calls(self) -> None:
        tc = ToolCall(id="tc_1", name="test", arguments={})
        msg = Message(role="assistant", tool_calls=(tc,))
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "test"

    def test_tool_message(self) -> None:
        msg = Message(role="tool", content="result", tool_call_id="tc_1")
        assert msg.role == "tool"
        assert msg.tool_call_id == "tc_1"

    def test_system_message(self) -> None:
        msg = Message(role="system", content="system prompt")
        assert msg.role == "system"

    def test_frozen(self) -> None:
        msg = Message(role="user", content="hello")
        with pytest.raises(AttributeError):
            msg.content = "changed"  # type: ignore[misc]


class TestTokenUsage:
    """TokenUsage tracks token counts."""

    def test_defaults(self) -> None:
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_with_values(self) -> None:
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50


class TestLLMResponse:
    """LLMResponse wraps parsed LLM output."""

    def test_text_response(self) -> None:
        resp = LLMResponse(content="Hello", stop_reason="end_turn")
        assert resp.content == "Hello"
        assert resp.tool_calls == ()
        assert resp.stop_reason == "end_turn"

    def test_tool_call_response(self) -> None:
        tc = ToolCall(id="tc_1", name="test", arguments={"x": 1})
        resp = LLMResponse(tool_calls=(tc,), stop_reason="tool_use")
        assert resp.content is None
        assert len(resp.tool_calls) == 1

    def test_usage_default(self) -> None:
        resp = LLMResponse()
        assert resp.usage.input_tokens == 0
        assert resp.usage.output_tokens == 0

    def test_with_usage(self) -> None:
        usage = TokenUsage(input_tokens=500, output_tokens=200)
        resp = LLMResponse(usage=usage)
        assert resp.usage.input_tokens == 500


class TestAgentResult:
    """AgentResult represents the final loop output."""

    def test_successful_result(self) -> None:
        result = AgentResult(
            answer="Found 5 patients",
            query="patients with diabetes",
            iterations=2,
            success=True,
        )
        assert result.answer == "Found 5 patients"
        assert result.query == "patients with diabetes"
        assert result.iterations == 2
        assert result.success is True
        assert result.tool_calls_made == ()

    def test_with_tool_calls(self) -> None:
        tc = ToolCall(id="tc_1", name="resolve", arguments={})
        result = AgentResult(
            answer="answer",
            query="query",
            tool_calls_made=(tc,),
        )
        assert len(result.tool_calls_made) == 1

    def test_defaults(self) -> None:
        result = AgentResult(answer="", query="")
        assert result.tool_calls_made == ()
        assert result.iterations == 0
        assert result.success is True

    def test_frozen(self) -> None:
        result = AgentResult(answer="x", query="y")
        with pytest.raises(AttributeError):
            result.answer = "changed"  # type: ignore[misc]
