"""Tests for saludai_agent.exceptions."""

from __future__ import annotations

import pytest

from saludai_agent.exceptions import (
    AgentError,
    AgentLoopError,
    LLMError,
    LLMResponseError,
    ToolExecutionError,
)
from saludai_core.exceptions import SaludAIError


class TestExceptionHierarchy:
    """Exception hierarchy follows the documented design."""

    def test_agent_error_is_saludai_error(self) -> None:
        assert issubclass(AgentError, SaludAIError)

    def test_agent_loop_error_is_agent_error(self) -> None:
        assert issubclass(AgentLoopError, AgentError)

    def test_tool_execution_error_is_agent_error(self) -> None:
        assert issubclass(ToolExecutionError, AgentError)

    def test_llm_error_is_saludai_error(self) -> None:
        assert issubclass(LLMError, SaludAIError)

    def test_llm_response_error_is_llm_error(self) -> None:
        assert issubclass(LLMResponseError, LLMError)

    def test_catch_all_agent_errors_with_agent_error(self) -> None:
        with pytest.raises(AgentError):
            raise AgentLoopError("max iterations")

        with pytest.raises(AgentError):
            raise ToolExecutionError("failed", tool_name="test", cause=None)

    def test_catch_all_with_saludai_error(self) -> None:
        with pytest.raises(SaludAIError):
            raise AgentLoopError("test")

        with pytest.raises(SaludAIError):
            raise LLMError("test")


class TestToolExecutionError:
    """ToolExecutionError carries extra attributes."""

    def test_attributes(self) -> None:
        cause = ValueError("bad input")
        exc = ToolExecutionError(
            "Tool failed",
            tool_name="resolve_terminology",
            cause=cause,
        )
        assert exc.tool_name == "resolve_terminology"
        assert exc.cause is cause
        assert str(exc) == "Tool failed"

    def test_without_cause(self) -> None:
        exc = ToolExecutionError("Tool failed", tool_name="search_fhir", cause=None)
        assert exc.cause is None
        assert exc.tool_name == "search_fhir"

    def test_is_catchable_as_tool_execution_error(self) -> None:
        with pytest.raises(ToolExecutionError):
            raise ToolExecutionError("test", tool_name="x", cause=None)
