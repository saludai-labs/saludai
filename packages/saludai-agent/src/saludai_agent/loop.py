"""Agent loop: the core orchestration of LLM tool-calling.

Implements a single-turn agent that takes a natural language query, uses the
LLM with tool calling to resolve terminology and search FHIR, and produces a
narrative answer.

Flow::

    User query (Spanish)
      → LLM receives system prompt + tool definitions
      → LLM calls resolve_terminology (to get SNOMED/CIE-10/LOINC codes)
      → LLM calls search_fhir (with resolved codes as FHIR search params)
      → LLM sees Bundle summary, generates narrative answer
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from saludai_agent.config import AgentConfig
from saludai_agent.exceptions import AgentLoopError, ToolExecutionError
from saludai_agent.prompts import SYSTEM_PROMPT
from saludai_agent.tools import ToolRegistry
from saludai_agent.tracing import NoOpTracer, _response_to_dict, _summarise_messages
from saludai_agent.types import AgentResult, Message, ToolCall, ToolResult

if TYPE_CHECKING:
    from saludai_agent.llm import LLMClient
    from saludai_agent.tracing import Tracer
    from saludai_core.fhir_client import FHIRClient
    from saludai_core.terminology import TerminologyResolver

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AgentLoop:
    """Single-turn agent loop with LLM tool calling.

    Takes injected dependencies for testability. The ``run()`` method
    orchestrates the full loop: send messages → execute tool calls → repeat
    → return narrative answer.

    Args:
        llm: LLM client for generation.
        fhir_client: FHIR client for search operations.
        terminology_resolver: Terminology resolver for code lookup.
        config: Agent configuration (defaults used if ``None``).
        tracer: Observability tracer (``None`` uses ``NoOpTracer``).
    """

    def __init__(
        self,
        llm: LLMClient,
        fhir_client: FHIRClient,
        terminology_resolver: TerminologyResolver | None = None,
        config: AgentConfig | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._llm = llm
        self._config = config or AgentConfig()
        self._tracer: Tracer = tracer or NoOpTracer()
        self._tool_registry = ToolRegistry(
            fhir_client=fhir_client,
            terminology_resolver=terminology_resolver,
        )

    async def run(self, query: str) -> AgentResult:
        """Execute the agent loop for a single query.

        Args:
            query: Natural language query from the user.

        Returns:
            An ``AgentResult`` with the narrative answer and metadata.

        Raises:
            AgentLoopError: If max iterations are exceeded.
        """
        logger.info("agent_loop_started", query=query)

        self._tracer.start_trace(
            name="agent_run",
            input={"query": query},
            metadata={
                "model": self._config.llm_model,
                "provider": self._config.llm_provider,
                "max_iterations": self._config.agent_max_iterations,
            },
        )

        messages: list[Message] = [Message(role="user", content=query)]
        all_tool_calls: list[ToolCall] = []
        tool_definitions = self._tool_registry.definitions()
        llm_call_count = 0

        try:
            for iteration in range(1, self._config.agent_max_iterations + 1):
                logger.info("agent_loop_iteration", iteration=iteration)

                response = await self._llm.generate(
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=tool_definitions if tool_definitions else None,
                    temperature=self._config.agent_temperature,
                    max_tokens=self._config.agent_max_tokens,
                )

                llm_call_count += 1
                self._tracer.log_generation(
                    name=f"llm_call_{llm_call_count}",
                    model=self._config.llm_model,
                    input={"messages": _summarise_messages(messages)},
                    output=_response_to_dict(response).get("content"),
                    usage=response.usage,
                )

                # If the LLM returns tool calls, execute them and continue
                if response.tool_calls:
                    all_tool_calls.extend(response.tool_calls)

                    # Append assistant message with tool calls
                    messages.append(
                        Message(
                            role="assistant",
                            content=response.content,
                            tool_calls=response.tool_calls,
                        )
                    )

                    # Execute each tool call and append results
                    for tool_call in response.tool_calls:
                        tool_result = await self._execute_tool(tool_call)
                        self._tracer.log_tool_call(
                            name=f"tool:{tool_call.name}",
                            input=tool_call.arguments,
                            output=tool_result.content,
                        )
                        messages.append(
                            Message(
                                role="tool",
                                content=tool_result.content,
                                tool_call_id=tool_result.tool_call_id,
                            )
                        )

                    continue

                # No tool calls — the LLM produced a final answer
                answer = response.content or ""
                logger.info(
                    "agent_loop_completed",
                    iterations=iteration,
                    tool_calls_made=len(all_tool_calls),
                    answer_length=len(answer),
                )

                trace_id, trace_url = self._tracer.end_trace(
                    output={
                        "answer": answer,
                        "iterations": iteration,
                        "tool_calls_made": len(all_tool_calls),
                    },
                )

                return AgentResult(
                    answer=answer,
                    query=query,
                    tool_calls_made=tuple(all_tool_calls),
                    iterations=iteration,
                    success=True,
                    trace_id=trace_id,
                    trace_url=trace_url,
                )

        except Exception:
            self._tracer.end_trace(output={"error": "agent_loop_failed"})
            raise

        # Exhausted max iterations without a final answer
        self._tracer.end_trace(
            output={"error": "max_iterations_exceeded"},
        )
        logger.warning(
            "agent_loop_max_iterations",
            max_iterations=self._config.agent_max_iterations,
        )
        raise AgentLoopError(
            f"Agent loop exceeded maximum iterations ({self._config.agent_max_iterations})"
        )

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call, catching errors gracefully.

        Tool errors are returned as error results to the LLM rather than
        crashing the loop, giving the LLM a chance to recover.

        Args:
            tool_call: The tool call to execute.

        Returns:
            A ``ToolResult`` (may have ``is_error=True``).
        """
        try:
            return await self._tool_registry.execute(tool_call)
        except ToolExecutionError as exc:
            logger.warning(
                "tool_execution_error_returned_to_llm",
                tool_name=tool_call.name,
                error=str(exc),
            )
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Error executing {tool_call.name}: {exc}",
                is_error=True,
            )
