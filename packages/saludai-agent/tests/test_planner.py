"""Tests for the Query Planner (ADR-009)."""

from __future__ import annotations

from typing import Any

import pytest

from saludai_agent.planner import (
    QueryPlan,
    _parse_plan,
    build_planning_prompt,
    format_plan_for_prompt,
    plan_query,
    resolve_tool_set,
)
from saludai_agent.types import LLMResponse, Message, TokenUsage
from saludai_core.locales import load_locale_pack

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ar_pack():
    return load_locale_pack("ar")


class FakePlannerLLM:
    """Fake LLM that returns a predetermined JSON plan."""

    def __init__(self, response_json: str) -> None:
        self._response = response_json
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self.calls.append({
            "system": system,
            "messages": messages,
            "tools": tools,
        })
        return LLMResponse(
            content=self._response,
            tool_calls=(),
            stop_reason="end_turn",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )


# ---------------------------------------------------------------------------
# _parse_plan tests
# ---------------------------------------------------------------------------


class TestParsePlan:
    """Tests for JSON parsing of planner output."""

    def test_valid_json(self) -> None:
        raw = (
            '{"question_type": "count", "strategy": "count_simple",'
            ' "terms_to_resolve": [], "reasoning": "simple count"}'
        )
        plan = _parse_plan(raw)
        assert plan.question_type == "count"
        assert plan.strategy == "count_simple"
        assert plan.terms_to_resolve == ()
        assert plan.reasoning == "simple count"

    def test_json_with_markdown_fences(self) -> None:
        raw = (
            '```json\n{"question_type": "list", "strategy":'
            ' "list_resources", "terms_to_resolve": ["diabetes"],'
            ' "reasoning": "list"}\n```'
        )
        plan = _parse_plan(raw)
        assert plan.question_type == "list"
        assert plan.strategy == "list_resources"
        assert plan.terms_to_resolve == ("diabetes",)

    def test_json_with_surrounding_text(self) -> None:
        raw = (
            'Here is the plan:\n{"question_type": "count",'
            ' "strategy": "count_with_condition",'
            ' "terms_to_resolve": ["DM2"],'
            ' "reasoning": "count patients with condition"}\nDone.'
        )
        plan = _parse_plan(raw)
        assert plan.question_type == "count"
        assert plan.terms_to_resolve == ("DM2",)

    def test_terms_as_string(self) -> None:
        raw = (
            '{"question_type": "count", "strategy": "count_simple",'
            ' "terms_to_resolve": "diabetes", "reasoning": "x"}'
        )
        plan = _parse_plan(raw)
        assert plan.terms_to_resolve == ("diabetes",)

    def test_invalid_json_returns_fallback(self) -> None:
        plan = _parse_plan("this is not json at all")
        assert plan.question_type == "unknown"
        assert plan.strategy == "search_include"

    def test_empty_string_returns_fallback(self) -> None:
        plan = _parse_plan("")
        assert plan.question_type == "unknown"

    def test_partial_json_returns_fallback(self) -> None:
        plan = _parse_plan('{"question_type": "count"')
        assert plan.question_type == "unknown"

    def test_missing_fields_use_defaults(self) -> None:
        raw = '{"question_type": "aggregation"}'
        plan = _parse_plan(raw)
        assert plan.question_type == "aggregation"
        assert plan.strategy == "search_include"
        assert plan.terms_to_resolve == ()
        assert plan.reasoning == ""


# ---------------------------------------------------------------------------
# build_planning_prompt tests
# ---------------------------------------------------------------------------


class TestBuildPlanningPrompt:
    """Tests for the planning prompt builder."""

    def test_includes_relationships(self, ar_pack) -> None:
        prompt = build_planning_prompt(ar_pack)
        assert "Condition --subject--> Patient" in prompt
        assert "Immunization --patient--> Patient" in prompt
        assert "AllergyIntolerance --patient--> Patient" in prompt

    def test_includes_patterns(self, ar_pack) -> None:
        prompt = build_planning_prompt(ar_pack)
        assert "count_simple" in prompt
        assert "count_with_condition" in prompt
        assert "multi_search" in prompt
        assert "_summary=count" in prompt

    def test_includes_examples(self, ar_pack) -> None:
        prompt = build_planning_prompt(ar_pack)
        assert "Patient?_summary=count" in prompt
        assert "_has:Condition:subject:code" in prompt

    def test_json_format_instructions(self, ar_pack) -> None:
        prompt = build_planning_prompt(ar_pack)
        assert "question_type" in prompt
        assert "strategy" in prompt
        assert "terms_to_resolve" in prompt


# ---------------------------------------------------------------------------
# format_plan_for_prompt tests
# ---------------------------------------------------------------------------


class TestFormatPlanForPrompt:
    """Tests for plan formatting for executor injection."""

    def test_includes_all_fields(self) -> None:
        plan = QueryPlan(
            question_type="count",
            strategy="count_with_condition",
            terms_to_resolve=("diabetes tipo 2",),
            reasoning="Count patients with condition",
        )
        text = format_plan_for_prompt(plan)
        assert "count" in text
        assert "count_with_condition" in text
        assert "diabetes tipo 2" in text
        assert "Count patients with condition" in text

    def test_no_terms(self) -> None:
        plan = QueryPlan(
            question_type="count",
            strategy="count_simple",
            terms_to_resolve=(),
            reasoning="Simple count",
        )
        text = format_plan_for_prompt(plan)
        assert "(ninguno)" in text

    def test_includes_fallback_guidance(self) -> None:
        plan = QueryPlan(
            question_type="count",
            strategy="count_simple",
            terms_to_resolve=(),
            reasoning="x",
        )
        text = format_plan_for_prompt(plan)
        assert "adaptarte" in text


# ---------------------------------------------------------------------------
# plan_query integration test
# ---------------------------------------------------------------------------


class TestPlanQuery:
    """Integration tests for plan_query with FakeLLMClient."""

    @pytest.mark.asyncio
    async def test_produces_valid_plan(self, ar_pack) -> None:
        fake_llm = FakePlannerLLM(
            '{"question_type": "count", "strategy": "count_with_condition", '
            '"terms_to_resolve": ["diabetes tipo 2"], '
            '"reasoning": "Count patients with DM2"}'
        )
        plan = await plan_query(fake_llm, "Cuantos pacientes con diabetes?", ar_pack)
        assert plan.question_type == "count"
        assert plan.strategy == "count_with_condition"
        assert plan.terms_to_resolve == ("diabetes tipo 2",)
        assert len(fake_llm.calls) == 1

    @pytest.mark.asyncio
    async def test_sends_no_tools(self, ar_pack) -> None:
        fake_llm = FakePlannerLLM(
            '{"question_type": "list", "strategy":'
            ' "list_resources", "terms_to_resolve": [],'
            ' "reasoning": "x"}'
        )
        await plan_query(fake_llm, "test", ar_pack)
        assert fake_llm.calls[0]["tools"] is None

    @pytest.mark.asyncio
    async def test_fallback_on_bad_response(self, ar_pack) -> None:
        fake_llm = FakePlannerLLM("I don't understand the question")
        plan = await plan_query(fake_llm, "test", ar_pack)
        assert plan.question_type == "unknown"
        assert plan.strategy == "search_include"

    @pytest.mark.asyncio
    async def test_prompt_contains_fhir_knowledge(self, ar_pack) -> None:
        fake_llm = FakePlannerLLM(
            '{"question_type": "count", "strategy":'
            ' "count_simple", "terms_to_resolve": [],'
            ' "reasoning": "x"}'
        )
        await plan_query(fake_llm, "test", ar_pack)
        system = fake_llm.calls[0]["system"]
        assert "Condition --subject--> Patient" in system
        assert "count_with_condition" in system


# ---------------------------------------------------------------------------
# resolve_tool_set tests (Action Space Reduction)
# ---------------------------------------------------------------------------


class TestResolveToolSet:
    """Tests for Action Space Reduction tool set resolution."""

    def test_count_simple_restricts_to_count_fhir(self, ar_pack) -> None:
        result = resolve_tool_set("count_simple", ar_pack.query_patterns)
        assert result == frozenset({"count_fhir"})

    def test_count_filtered_includes_resolve_and_count(self, ar_pack) -> None:
        result = resolve_tool_set("count_filtered", ar_pack.query_patterns)
        assert result == frozenset({"resolve_terminology", "count_fhir"})

    def test_count_with_condition_includes_resolve_and_count(
        self, ar_pack
    ) -> None:
        result = resolve_tool_set(
            "count_with_condition", ar_pack.query_patterns
        )
        assert result == frozenset({"resolve_terminology", "count_fhir"})

    def test_multi_search_returns_none_for_all_tools(self, ar_pack) -> None:
        result = resolve_tool_set("multi_search", ar_pack.query_patterns)
        assert result is None

    def test_search_include_has_four_tools(self, ar_pack) -> None:
        result = resolve_tool_set("search_include", ar_pack.query_patterns)
        assert result == frozenset({
            "resolve_terminology",
            "search_fhir",
            "get_resource",
            "execute_code",
        })

    def test_unknown_strategy_returns_none(self, ar_pack) -> None:
        result = resolve_tool_set(
            "nonexistent_strategy", ar_pack.query_patterns
        )
        assert result is None

    def test_empty_patterns_returns_none(self) -> None:
        result = resolve_tool_set("count_simple", ())
        assert result is None

    def test_temporal_includes_count_and_search(self, ar_pack) -> None:
        result = resolve_tool_set("temporal", ar_pack.query_patterns)
        assert "count_fhir" in result
        assert "search_fhir" in result
        assert "resolve_terminology" in result
        assert "execute_code" in result
