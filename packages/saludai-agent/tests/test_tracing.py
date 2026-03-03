"""Tests for saludai_agent.tracing — Langfuse integration."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from saludai_agent.config import AgentConfig
from saludai_agent.tracing import (
    LangfuseTracer,
    NoOpTracer,
    Tracer,
    _response_to_dict,
    _summarise_messages,
    create_tracer,
)
from saludai_agent.types import LLMResponse, Message, TokenUsage, ToolCall

# ---------------------------------------------------------------------------
# TestNoOpTracer
# ---------------------------------------------------------------------------


class TestNoOpTracer:
    """NoOpTracer silently discards all events."""

    def test_implements_protocol(self) -> None:
        assert isinstance(NoOpTracer(), Tracer)

    def test_start_trace(self) -> None:
        tracer = NoOpTracer()
        tracer.start_trace(name="test", input={"query": "hello"})

    def test_log_generation(self) -> None:
        tracer = NoOpTracer()
        usage = TokenUsage(input_tokens=10, output_tokens=20)
        tracer.log_generation(
            name="llm_call_1",
            model="test-model",
            input={"messages": "user: hello"},
            output="world",
            usage=usage,
        )

    def test_log_tool_call(self) -> None:
        tracer = NoOpTracer()
        tracer.log_tool_call(
            name="tool:resolve_terminology",
            input={"term": "diabetes"},
            output='{"code": "44054006"}',
        )

    def test_end_trace_returns_none(self) -> None:
        tracer = NoOpTracer()
        trace_id, trace_url = tracer.end_trace(output={"answer": "test"})
        assert trace_id is None
        assert trace_url is None

    def test_flush(self) -> None:
        tracer = NoOpTracer()
        tracer.flush()


# ---------------------------------------------------------------------------
# TestLangfuseTracer
# ---------------------------------------------------------------------------


class TestLangfuseTracer:
    """LangfuseTracer delegates to the Langfuse SDK v3."""

    def _make_mock_langfuse(self) -> MagicMock:
        """Create a mock Langfuse v3 client with span mocks."""
        mock_generation = MagicMock()
        mock_tool_span = MagicMock()

        mock_root_span = MagicMock()
        mock_root_span.trace_id = "trace-abc-123"
        mock_root_span.start_generation.return_value = mock_generation
        mock_root_span.start_span.return_value = mock_tool_span

        mock_client = MagicMock()
        mock_client.start_span.return_value = mock_root_span
        mock_client.get_trace_url.return_value = "https://langfuse.example.com/trace/abc-123"
        return mock_client

    def test_implements_protocol(self) -> None:
        mock_client = self._make_mock_langfuse()
        assert isinstance(LangfuseTracer(langfuse_client=mock_client), Tracer)

    def test_start_trace_calls_langfuse(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)

        tracer.start_trace(
            name="agent_run",
            input={"query": "diabetes"},
            metadata={"model": "test"},
        )

        mock_client.start_span.assert_called_once_with(
            name="agent_run",
            input={"query": "diabetes"},
            metadata={"model": "test"},
        )

    def test_start_trace_default_metadata(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)

        tracer.start_trace(name="test", input={})

        mock_client.start_span.assert_called_once_with(
            name="test",
            input={},
            metadata={},
        )

    def test_log_generation_creates_generation(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        tracer.start_trace(name="test", input={})

        usage = TokenUsage(input_tokens=100, output_tokens=50)
        tracer.log_generation(
            name="llm_call_1",
            model="claude-test",
            input={"messages": "user: hello"},
            output="response text",
            usage=usage,
        )

        mock_root_span = mock_client.start_span.return_value
        mock_root_span.start_generation.assert_called_once_with(
            name="llm_call_1",
            model="claude-test",
            input={"messages": "user: hello"},
            output="response text",
            usage_details={"input": 100, "output": 50},
        )
        mock_root_span.start_generation.return_value.end.assert_called_once()

    def test_log_generation_no_trace_is_safe(self) -> None:
        """log_generation before start_trace does nothing."""
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        usage = TokenUsage()
        tracer.log_generation(name="llm_call_1", model="test", input={}, output=None, usage=usage)

    def test_log_tool_call_creates_span(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        tracer.start_trace(name="test", input={})

        tracer.log_tool_call(
            name="tool:search_fhir",
            input={"resource_type": "Patient"},
            output='{"total": 5}',
        )

        mock_root_span = mock_client.start_span.return_value
        mock_root_span.start_span.assert_called_once_with(
            name="tool:search_fhir",
            input={"resource_type": "Patient"},
            output='{"total": 5}',
        )
        mock_root_span.start_span.return_value.end.assert_called_once()

    def test_log_tool_call_no_trace_is_safe(self) -> None:
        """log_tool_call before start_trace does nothing."""
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        tracer.log_tool_call(name="tool:test", input={}, output="")

    def test_end_trace_returns_id_and_url(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        tracer.start_trace(name="test", input={})

        trace_id, trace_url = tracer.end_trace(output={"answer": "done"})

        assert trace_id == "trace-abc-123"
        assert trace_url == "https://langfuse.example.com/trace/abc-123"
        mock_root_span = mock_client.start_span.return_value
        mock_root_span.update.assert_called_once_with(output={"answer": "done"})
        mock_root_span.end.assert_called_once()

    def test_end_trace_no_trace_returns_none(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        trace_id, trace_url = tracer.end_trace(output={})
        assert trace_id is None
        assert trace_url is None

    def test_flush_calls_langfuse_flush(self) -> None:
        mock_client = self._make_mock_langfuse()
        tracer = LangfuseTracer(langfuse_client=mock_client)
        tracer.flush()
        mock_client.flush.assert_called_once()


# ---------------------------------------------------------------------------
# TestCreateTracer
# ---------------------------------------------------------------------------


class TestCreateTracer:
    """Factory returns the correct tracer type."""

    def test_disabled_returns_noop(self) -> None:
        config = AgentConfig(langfuse_enabled=False)
        tracer = create_tracer(config)
        assert isinstance(tracer, NoOpTracer)

    def test_enabled_returns_langfuse_tracer(self) -> None:
        mock_langfuse_cls = MagicMock()
        mock_langfuse_cls.return_value = MagicMock()
        fake_module = ModuleType("langfuse")
        fake_module.Langfuse = mock_langfuse_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"langfuse": fake_module}):
            config = AgentConfig(langfuse_enabled=True)
            tracer = create_tracer(config)
            assert isinstance(tracer, LangfuseTracer)
            mock_langfuse_cls.assert_called_once()

    def test_enabled_but_init_fails_returns_noop(self) -> None:
        mock_langfuse_cls = MagicMock(side_effect=Exception("no keys"))
        fake_module = ModuleType("langfuse")
        fake_module.Langfuse = mock_langfuse_cls  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"langfuse": fake_module}):
            config = AgentConfig(langfuse_enabled=True)
            tracer = create_tracer(config)
            assert isinstance(tracer, NoOpTracer)


# ---------------------------------------------------------------------------
# TestHelpers
# ---------------------------------------------------------------------------


class TestSummariseMessages:
    """Tests for _summarise_messages helper."""

    def test_user_message(self) -> None:
        messages = [Message(role="user", content="hello world")]
        result = _summarise_messages(messages)
        assert "user: hello world" in result

    def test_long_content_truncated(self) -> None:
        long_text = "x" * 300
        messages = [Message(role="user", content=long_text)]
        result = _summarise_messages(messages)
        assert "..." in result
        assert len(result) < 300

    def test_tool_call_message(self) -> None:
        tc = ToolCall(id="tc_1", name="search_fhir", arguments={})
        messages = [Message(role="assistant", tool_calls=(tc,))]
        result = _summarise_messages(messages)
        assert "tool_calls: search_fhir" in result


class TestResponseToDict:
    """Tests for _response_to_dict helper."""

    def test_content_only(self) -> None:
        response = LLMResponse(content="hello", stop_reason="end_turn")
        result = _response_to_dict(response)
        assert result["content"] == "hello"
        assert result["stop_reason"] == "end_turn"
        assert "tool_calls" not in result

    def test_with_tool_calls(self) -> None:
        tc = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "test"})
        response = LLMResponse(tool_calls=(tc,), stop_reason="tool_use")
        result = _response_to_dict(response)
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "resolve_terminology"

    def test_no_content(self) -> None:
        response = LLMResponse(stop_reason="end_turn")
        result = _response_to_dict(response)
        assert "content" not in result
