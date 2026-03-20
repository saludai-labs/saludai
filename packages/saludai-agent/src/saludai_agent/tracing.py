"""Tracing infrastructure for the agent loop.

Provides a ``Tracer`` protocol with four implementations:

- ``LangfuseTracer``: sends traces to Langfuse Cloud/self-hosted.
- ``NoOpTracer``: silent no-op when tracing is disabled.
- ``RecordingTracer``: captures all events in memory for post-run analysis.
- ``CompositeTracer``: delegates to multiple child tracers simultaneously.

The ``create_tracer`` factory selects ``LangfuseTracer`` or ``NoOpTracer``
based on ``AgentConfig``. Combine with ``RecordingTracer`` via
``CompositeTracer`` for offline debugging alongside Langfuse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import structlog

if TYPE_CHECKING:
    from saludai_agent.config import AgentConfig
    from saludai_agent.types import TokenUsage

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Tracer(Protocol):
    """Observability tracer for the agent loop."""

    def start_trace(
        self,
        name: str,
        input: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Begin a new trace for an agent run.

        Args:
            name: Trace name (e.g. ``"agent_run"``).
            input: Input data (typically ``{"query": ...}``).
            metadata: Optional metadata (model, provider, etc.).
        """
        ...

    def log_generation(
        self,
        name: str,
        model: str,
        input: dict[str, Any],
        output: str | None,
        usage: TokenUsage,
    ) -> None:
        """Log an LLM generation within the current trace.

        Args:
            name: Generation name (e.g. ``"llm_call_1"``).
            model: Model identifier.
            input: Summarised input (messages snapshot).
            output: LLM text output.
            usage: Token usage statistics.
        """
        ...

    def log_tool_call(
        self,
        name: str,
        input: dict[str, Any],
        output: str,
    ) -> None:
        """Log a tool execution within the current trace.

        Args:
            name: Tool name (e.g. ``"tool:resolve_terminology"``).
            input: Tool arguments.
            output: Tool result string.
        """
        ...

    def end_trace(self, output: dict[str, Any]) -> tuple[str | None, str | None]:
        """End the current trace.

        Args:
            output: Final output data (answer, metadata).

        Returns:
            A ``(trace_id, trace_url)`` tuple. Both ``None`` for no-op.
        """
        ...

    def flush(self) -> None:
        """Flush any pending events to the backend."""
        ...


# ---------------------------------------------------------------------------
# NoOpTracer
# ---------------------------------------------------------------------------


class NoOpTracer:
    """Silent tracer that discards all events."""

    def start_trace(
        self,
        name: str,
        input: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    def log_generation(
        self,
        name: str,
        model: str,
        input: dict[str, Any],
        output: str | None,
        usage: TokenUsage,
    ) -> None:
        pass

    def log_tool_call(
        self,
        name: str,
        input: dict[str, Any],
        output: str,
    ) -> None:
        pass

    def end_trace(self, output: dict[str, Any]) -> tuple[str | None, str | None]:
        return (None, None)

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------------------
# LangfuseTracer
# ---------------------------------------------------------------------------


class LangfuseTracer:
    """Tracer that sends events to Langfuse (SDK v3).

    The Langfuse SDK reads ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``,
    and ``LANGFUSE_HOST`` from environment variables automatically.

    Uses the v3 span-based API: ``start_span`` creates the root trace span,
    nested ``start_generation`` / ``start_span`` create children.

    Args:
        langfuse_client: An initialised ``langfuse.Langfuse`` instance.
    """

    def __init__(self, langfuse_client: Any) -> None:
        self._langfuse = langfuse_client
        self._root_span: Any | None = None
        self._trace_id: str | None = None

    def start_trace(
        self,
        name: str,
        input: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new Langfuse root span (acts as the trace)."""
        self._root_span = self._langfuse.start_span(
            name=name,
            input=input,
            metadata=metadata or {},
        )
        self._trace_id = self._root_span.trace_id
        logger.debug("langfuse_trace_started", trace_id=self._trace_id)

    def log_generation(
        self,
        name: str,
        model: str,
        input: dict[str, Any],
        output: str | None,
        usage: TokenUsage,
    ) -> None:
        """Create a generation span inside the current trace."""
        if self._root_span is None:
            return
        usage_details: dict[str, int] = {
            "input": usage.input_tokens,
            "output": usage.output_tokens,
        }
        if usage.cache_creation_input_tokens:
            usage_details["cache_creation_input_tokens"] = (
                usage.cache_creation_input_tokens
            )
        if usage.cache_read_input_tokens:
            usage_details["cache_read_input_tokens"] = (
                usage.cache_read_input_tokens
            )
        gen = self._root_span.start_generation(
            name=name,
            model=model,
            input=input,
            output=output,
            usage_details=usage_details,
        )
        gen.end()

    def log_tool_call(
        self,
        name: str,
        input: dict[str, Any],
        output: str,
    ) -> None:
        """Create a span for a tool execution inside the current trace."""
        if self._root_span is None:
            return
        span = self._root_span.start_span(
            name=name,
            input=input,
            output=output,
        )
        span.end()

    def end_trace(self, output: dict[str, Any]) -> tuple[str | None, str | None]:
        """Finalise the root span and return trace ID and URL.

        Returns:
            A ``(trace_id, trace_url)`` tuple.
        """
        if self._root_span is None:
            return (None, None)

        self._root_span.update(output=output)
        self._root_span.end()
        trace_url = self._langfuse.get_trace_url(trace_id=self._trace_id)
        logger.debug("langfuse_trace_ended", trace_id=self._trace_id, trace_url=trace_url)
        return (self._trace_id, trace_url)

    def flush(self) -> None:
        """Flush pending events to Langfuse."""
        self._langfuse.flush()


# ---------------------------------------------------------------------------
# RecordingTracer
# ---------------------------------------------------------------------------


class RecordingTracer:
    """Tracer that records all events in memory for post-run analysis.

    Implements the ``Tracer`` protocol without touching the agent loop.
    After each agent run, call ``get_recording()`` to retrieve a
    JSON-serializable dict with the query plan and per-iteration steps.

    Args:
        result_preview_limit: Max characters for tool result previews.
    """

    def __init__(self, result_preview_limit: int = 500) -> None:
        self._preview_limit = result_preview_limit
        self._plan: dict[str, Any] | None = None
        self._steps: list[dict[str, Any]] = []
        self._iteration = 0

    def start_trace(
        self,
        name: str,
        input: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Reset recording state for a new agent run."""
        self._plan = None
        self._steps = []
        self._iteration = 0

    def log_generation(
        self,
        name: str,
        model: str,
        input: dict[str, Any],
        output: str | None,
        usage: TokenUsage,
    ) -> None:
        """Record an LLM generation.

        Planner generations are stored separately. Other generations
        start a new iteration step.
        """
        if name == "planner":
            self._plan = {
                "model": model,
                "output": output,
            }
            return

        self._iteration += 1
        usage_dict: dict[str, int] = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }
        if usage.cache_creation_input_tokens:
            usage_dict["cache_creation_input_tokens"] = usage.cache_creation_input_tokens
        if usage.cache_read_input_tokens:
            usage_dict["cache_read_input_tokens"] = usage.cache_read_input_tokens
        self._steps.append({
            "iteration": self._iteration,
            "llm_output": output,
            "tool_calls": [],
            "usage": usage_dict,
        })

    def log_tool_call(
        self,
        name: str,
        input: dict[str, Any],
        output: str,
    ) -> None:
        """Record a tool execution in the current iteration step."""
        if not self._steps:
            return

        preview = output
        if len(output) > self._preview_limit:
            preview = output[: self._preview_limit] + "..."

        tool_name = name.removeprefix("tool:")

        self._steps[-1]["tool_calls"].append({
            "name": tool_name,
            "arguments": input,
            "result_preview": preview,
        })

    def end_trace(self, output: dict[str, Any]) -> tuple[str | None, str | None]:
        """End the recording (no trace ID to return)."""
        return (None, None)

    def flush(self) -> None:
        """No-op (nothing to flush)."""

    def get_recording(self) -> dict[str, Any]:
        """Return the recorded trace as a JSON-serializable dict.

        Returns:
            Dict with ``plan`` (nullable) and ``steps`` (list of iteration
            dicts, each with ``iteration``, ``llm_output``, ``tool_calls``,
            and ``usage``).
        """
        return {
            "plan": self._plan,
            "steps": list(self._steps),
        }


# ---------------------------------------------------------------------------
# CompositeTracer
# ---------------------------------------------------------------------------


class CompositeTracer:
    """Tracer that delegates to multiple child tracers.

    Useful for combining Langfuse tracing with in-memory recording
    without modifying the agent loop.

    Args:
        tracers: Child tracers to delegate to.
    """

    def __init__(self, *tracers: Tracer) -> None:
        self._tracers = tracers

    def start_trace(
        self,
        name: str,
        input: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        for t in self._tracers:
            t.start_trace(name, input, metadata)

    def log_generation(
        self,
        name: str,
        model: str,
        input: dict[str, Any],
        output: str | None,
        usage: TokenUsage,
    ) -> None:
        for t in self._tracers:
            t.log_generation(name, model, input, output, usage)

    def log_tool_call(
        self,
        name: str,
        input: dict[str, Any],
        output: str,
    ) -> None:
        for t in self._tracers:
            t.log_tool_call(name, input, output)

    def end_trace(self, output: dict[str, Any]) -> tuple[str | None, str | None]:
        """Delegate to all tracers, return the first non-None trace ID."""
        result: tuple[str | None, str | None] = (None, None)
        for t in self._tracers:
            trace_id, trace_url = t.end_trace(output)
            if result[0] is None and trace_id is not None:
                result = (trace_id, trace_url)
        return result

    def flush(self) -> None:
        for t in self._tracers:
            t.flush()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _summarise_messages(messages: list[Any]) -> str:
    """Create a compact summary of messages for trace input."""
    parts: list[str] = []
    for msg in messages:
        role = getattr(msg, "role", "unknown")
        content = getattr(msg, "content", None) or ""
        preview = content[:200] + "..." if len(content) > 200 else content
        tool_calls = getattr(msg, "tool_calls", ())
        if tool_calls:
            tc_names = ", ".join(tc.name for tc in tool_calls)
            parts.append(f"{role}: [tool_calls: {tc_names}]")
        else:
            parts.append(f"{role}: {preview}")
    return "\n".join(parts)


def _response_to_dict(response: Any) -> dict[str, Any]:
    """Convert an LLMResponse to a JSON-safe dict for trace logging."""
    result: dict[str, Any] = {}
    if response.content:
        result["content"] = response.content
    if response.tool_calls:
        result["tool_calls"] = [
            {"name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls
        ]
    result["stop_reason"] = response.stop_reason
    return result


def create_tracer(config: AgentConfig) -> Tracer:
    """Create the appropriate tracer based on configuration.

    Returns a ``LangfuseTracer`` if ``config.langfuse_enabled`` is ``True``
    and the Langfuse SDK initialises successfully. Falls back to
    ``NoOpTracer`` otherwise.

    Args:
        config: Agent configuration.

    Returns:
        A ``Tracer`` instance.
    """
    if not config.langfuse_enabled:
        logger.debug("langfuse_disabled")
        return NoOpTracer()

    try:
        from langfuse import Langfuse

        client = Langfuse()
        logger.info("langfuse_tracer_created")
        return LangfuseTracer(langfuse_client=client)
    except Exception as exc:
        logger.warning("langfuse_init_failed", error=str(exc))
        return NoOpTracer()
