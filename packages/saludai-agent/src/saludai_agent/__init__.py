"""SaludAI Agent — Self-reasoning FHIR agent loop."""

from __future__ import annotations

__version__ = "0.1.0"

from saludai_agent.config import AgentConfig
from saludai_agent.exceptions import (
    AgentError,
    AgentLoopError,
    LLMError,
    LLMResponseError,
    ToolExecutionError,
)
from saludai_agent.llm import (
    AnthropicLLMClient,
    LLMClient,
    OpenAILLMClient,
    create_llm_client,
)
from saludai_agent.loop import AgentLoop
from saludai_agent.planner import QueryPlan
from saludai_agent.tracing import (
    CompositeTracer,
    LangfuseTracer,
    NoOpTracer,
    RecordingTracer,
    Tracer,
    create_tracer,
)
from saludai_agent.types import AgentResult, LLMResponse, Message, TokenUsage, ToolCall, ToolResult

__all__ = [
    "AgentConfig",
    "AgentError",
    "AgentLoop",
    "AgentLoopError",
    "AgentResult",
    "AnthropicLLMClient",
    "CompositeTracer",
    "LLMClient",
    "LLMError",
    "LLMResponse",
    "LLMResponseError",
    "LangfuseTracer",
    "Message",
    "NoOpTracer",
    "OpenAILLMClient",
    "QueryPlan",
    "RecordingTracer",
    "TokenUsage",
    "ToolCall",
    "ToolExecutionError",
    "ToolResult",
    "Tracer",
    "create_llm_client",
    "create_tracer",
]
