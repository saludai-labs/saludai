"""SaludAI Agent exception hierarchy.

All agent exceptions inherit from ``SaludAIError`` (via ``AgentError``) so
callers can catch the whole family with a single ``except SaludAIError``.
"""

from __future__ import annotations

from saludai_core.exceptions import SaludAIError


class AgentError(SaludAIError):
    """Base exception for all agent errors."""


class AgentLoopError(AgentError):
    """Loop failures such as hitting max iterations or unexpected state."""


class ToolExecutionError(AgentError):
    """A tool failed during execution.

    Attributes:
        tool_name: Name of the tool that failed.
        cause: The underlying exception, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        tool_name: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.cause = cause


class LLMError(SaludAIError):
    """LLM communication failures (timeouts, auth, rate limits)."""


class LLMResponseError(LLMError):
    """Malformed or unexpected LLM responses."""
