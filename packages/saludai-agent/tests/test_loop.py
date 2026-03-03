"""Tests for saludai_agent.loop — full agent loop orchestration."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from saludai_agent.config import AgentConfig
from saludai_agent.exceptions import AgentLoopError
from saludai_agent.loop import AgentLoop
from saludai_agent.types import LLMResponse, ToolCall

# ---------------------------------------------------------------------------
# FakeLLMClient — returns scripted responses
# ---------------------------------------------------------------------------


class FakeLLMClient:
    """Test double that returns pre-configured LLM responses in order."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = iter(responses)
        self.calls: list[dict[str, Any]] = []

    async def generate(self, **kwargs: Any) -> LLMResponse:
        self.calls.append(kwargs)
        return next(self._responses)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fhir_client(bundle: Any = None) -> MagicMock:
    """Create a mock FHIRClient."""
    if bundle is None:
        bundle = MagicMock()
        bundle.entry = None
        bundle.total = 0

    client = MagicMock()
    client.search = AsyncMock(return_value=bundle)
    return client


def _make_terminology_resolver(
    code: str = "44054006",
    display: str = "Diabetes mellitus tipo 2",
    system_value: str = "http://snomed.info/sct",
) -> MagicMock:
    """Create a mock TerminologyResolver."""
    concept = MagicMock()
    concept.code = code
    concept.system = MagicMock()
    concept.system.value = system_value
    concept.display = display

    match = MagicMock()
    match.concept = concept
    match.score = 100.0
    match.match_type = MagicMock()
    match.match_type.value = "exact_display"
    match.query = "diabetes tipo 2"
    match.is_confident = True

    resolver = MagicMock()
    resolver.resolve.return_value = match
    return resolver


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentLoopDirectAnswer:
    """Agent produces a direct answer without tool calls."""

    @pytest.mark.asyncio
    async def test_direct_answer(self) -> None:
        llm = FakeLLMClient(
            [
                LLMResponse(content="No tengo herramientas para eso.", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        result = await loop.run("¿Qué hora es?")
        assert result.success is True
        assert result.answer == "No tengo herramientas para eso."
        assert result.query == "¿Qué hora es?"
        assert result.iterations == 1
        assert result.tool_calls_made == ()

    @pytest.mark.asyncio
    async def test_empty_answer(self) -> None:
        llm = FakeLLMClient(
            [
                LLMResponse(content=None, stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        result = await loop.run("test")
        assert result.answer == ""
        assert result.success is True


class TestAgentLoopWithToolCalls:
    """Agent uses tools then produces a final answer."""

    @pytest.mark.asyncio
    async def test_single_tool_call_then_answer(self) -> None:
        """LLM calls resolve_terminology then answers."""
        resolve_tc = ToolCall(
            id="tc_1",
            name="resolve_terminology",
            arguments={"term": "diabetes tipo 2"},
        )
        llm = FakeLLMClient(
            [
                # Iteration 1: LLM requests tool call
                LLMResponse(tool_calls=(resolve_tc,), stop_reason="tool_use"),
                # Iteration 2: LLM produces final answer
                LLMResponse(
                    content="Se encontró el código SNOMED CT 44054006.",
                    stop_reason="end_turn",
                ),
            ]
        )
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client, terminology_resolver=resolver)

        result = await loop.run("Buscar diabetes tipo 2")
        assert result.success is True
        assert result.iterations == 2
        assert len(result.tool_calls_made) == 1
        assert result.tool_calls_made[0].name == "resolve_terminology"

    @pytest.mark.asyncio
    async def test_two_tool_calls_then_answer(self) -> None:
        """LLM calls resolve_terminology, then search_fhir, then answers."""
        resolve_tc = ToolCall(
            id="tc_1",
            name="resolve_terminology",
            arguments={"term": "diabetes tipo 2"},
        )
        search_tc = ToolCall(
            id="tc_2",
            name="search_fhir",
            arguments={
                "resource_type": "Condition",
                "params": {"code": "http://snomed.info/sct|44054006"},
            },
        )
        llm = FakeLLMClient(
            [
                LLMResponse(tool_calls=(resolve_tc,), stop_reason="tool_use"),
                LLMResponse(tool_calls=(search_tc,), stop_reason="tool_use"),
                LLMResponse(
                    content="Encontré 5 condiciones de diabetes.",
                    stop_reason="end_turn",
                ),
            ]
        )
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client, terminology_resolver=resolver)

        result = await loop.run("Pacientes con diabetes tipo 2")
        assert result.success is True
        assert result.iterations == 3
        assert len(result.tool_calls_made) == 2
        assert result.tool_calls_made[0].name == "resolve_terminology"
        assert result.tool_calls_made[1].name == "search_fhir"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_single_response(self) -> None:
        """LLM requests two tool calls in one response."""
        tc1 = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "diabetes"})
        tc2 = ToolCall(id="tc_2", name="resolve_terminology", arguments={"term": "hipertensión"})
        llm = FakeLLMClient(
            [
                LLMResponse(tool_calls=(tc1, tc2), stop_reason="tool_use"),
                LLMResponse(content="Ambos códigos encontrados.", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client, terminology_resolver=resolver)

        result = await loop.run("Buscar diabetes e hipertensión")
        assert result.success is True
        assert result.iterations == 2
        assert len(result.tool_calls_made) == 2


class TestAgentLoopMaxIterations:
    """Max iterations cap prevents runaway loops."""

    @pytest.mark.asyncio
    async def test_max_iterations_exceeded(self) -> None:
        """Loop raises AgentLoopError when max iterations hit."""
        tc = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "test"})
        # Every response requests another tool call — will never finish
        responses = [LLMResponse(tool_calls=(tc,), stop_reason="tool_use") for _ in range(10)]
        llm = FakeLLMClient(responses)
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()
        config = AgentConfig(agent_max_iterations=3)

        loop = AgentLoop(
            llm=llm,
            fhir_client=fhir_client,
            terminology_resolver=resolver,
            config=config,
        )

        with pytest.raises(AgentLoopError, match="maximum iterations"):
            await loop.run("infinite loop query")

    @pytest.mark.asyncio
    async def test_finishes_at_exactly_max_iterations(self) -> None:
        """Agent that answers on the last iteration succeeds."""
        tc = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "test"})
        config = AgentConfig(agent_max_iterations=2)
        llm = FakeLLMClient(
            [
                LLMResponse(tool_calls=(tc,), stop_reason="tool_use"),
                LLMResponse(content="Final answer", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()

        loop = AgentLoop(
            llm=llm,
            fhir_client=fhir_client,
            terminology_resolver=resolver,
            config=config,
        )
        result = await loop.run("test")
        assert result.success is True
        assert result.iterations == 2


class TestAgentLoopErrorHandling:
    """Tool errors are returned to the LLM gracefully."""

    @pytest.mark.asyncio
    async def test_tool_error_returned_to_llm(self) -> None:
        """When a tool fails, the error is sent back as a tool result."""
        tc = ToolCall(
            id="tc_1",
            name="search_fhir",
            arguments={"resource_type": "Patient"},
        )
        llm = FakeLLMClient(
            [
                LLMResponse(tool_calls=(tc,), stop_reason="tool_use"),
                LLMResponse(
                    content="Lo siento, hubo un error en la búsqueda.",
                    stop_reason="end_turn",
                ),
            ]
        )
        # FHIRClient.search raises an exception
        fhir_client = MagicMock()
        fhir_client.search = AsyncMock(side_effect=Exception("Connection refused"))

        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        result = await loop.run("Buscar pacientes")
        assert result.success is True
        assert result.iterations == 2
        # The LLM saw the error and produced a graceful response
        assert "error" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self) -> None:
        """Unknown tool calls return an error result, not crash."""
        tc = ToolCall(id="tc_1", name="nonexistent_tool", arguments={})
        llm = FakeLLMClient(
            [
                LLMResponse(tool_calls=(tc,), stop_reason="tool_use"),
                LLMResponse(content="I don't have that tool.", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        # Unknown tools return error result via registry, not ToolExecutionError
        result = await loop.run("test")
        assert result.success is True
        assert result.iterations == 2


class TestAgentLoopMessages:
    """Verify messages passed to the LLM at each step."""

    @pytest.mark.asyncio
    async def test_first_call_has_user_message(self) -> None:
        llm = FakeLLMClient(
            [
                LLMResponse(content="answer", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        await loop.run("my query")
        assert len(llm.calls) == 1
        messages = llm.calls[0]["messages"]
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "my query"

    @pytest.mark.asyncio
    async def test_system_prompt_passed(self) -> None:
        llm = FakeLLMClient(
            [
                LLMResponse(content="answer", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        await loop.run("test")
        assert "system" in llm.calls[0]
        assert len(llm.calls[0]["system"]) > 50

    @pytest.mark.asyncio
    async def test_tool_result_appended_after_call(self) -> None:
        tc = ToolCall(id="tc_1", name="resolve_terminology", arguments={"term": "diabetes"})
        llm = FakeLLMClient(
            [
                LLMResponse(tool_calls=(tc,), stop_reason="tool_use"),
                LLMResponse(content="done", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client, terminology_resolver=resolver)

        await loop.run("diabetes")
        # Second call should have: user, assistant (tool call), tool result
        messages = llm.calls[1]["messages"]
        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert len(messages[1].tool_calls) == 1
        assert messages[2].role == "tool"
        assert messages[2].tool_call_id == "tc_1"

    @pytest.mark.asyncio
    async def test_tools_definitions_passed(self) -> None:
        llm = FakeLLMClient(
            [
                LLMResponse(content="answer", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        resolver = _make_terminology_resolver()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client, terminology_resolver=resolver)

        await loop.run("test")
        tools = llm.calls[0]["tools"]
        assert tools is not None
        tool_names = {t["name"] for t in tools}
        assert "resolve_terminology" in tool_names
        assert "search_fhir" in tool_names

    @pytest.mark.asyncio
    async def test_temperature_and_max_tokens_from_config(self) -> None:
        config = AgentConfig(agent_temperature=0.5, agent_max_tokens=2048)
        llm = FakeLLMClient(
            [
                LLMResponse(content="answer", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client, config=config)

        await loop.run("test")
        assert llm.calls[0]["temperature"] == 0.5
        assert llm.calls[0]["max_tokens"] == 2048


class TestAgentLoopDefaultConfig:
    """AgentLoop uses default config when none provided."""

    @pytest.mark.asyncio
    async def test_default_config(self) -> None:
        llm = FakeLLMClient(
            [
                LLMResponse(content="answer", stop_reason="end_turn"),
            ]
        )
        fhir_client = _make_fhir_client()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)

        result = await loop.run("test")
        assert result.success is True
        # Default temperature=0.0
        assert llm.calls[0]["temperature"] == 0.0
