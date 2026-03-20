"""Query planner: classifies questions and produces FHIR query plans.

Implements the planning phase of the Plan-and-Execute pattern (ADR-009).
Uses a single LLM call (no tools) to classify the user's question and
select an optimal FHIR query strategy from a structured catalog.

The FHIR knowledge (resource graph + query patterns) comes from the locale
pack, not from LLM memorization.  This ensures correctness and testability.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from saludai_agent.llm import LLMClient
    from saludai_core.locales._types import LocalePack, QueryPattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# QueryPlan — output of the planning phase
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """Structured plan produced by the planner for the executor.

    Attributes:
        question_type: Classification of the question (e.g. ``"count_filtered"``).
        strategy: Selected query pattern name from the catalog.
        terms_to_resolve: Medical terms that need terminology resolution.
        reasoning: Brief explanation of why this strategy was chosen.
        raw_json: The raw JSON string from the LLM (for tracing/debugging).
    """

    question_type: str
    strategy: str
    terms_to_resolve: tuple[str, ...]
    reasoning: str
    raw_json: str = ""


# ---------------------------------------------------------------------------
# Planning prompt builder
# ---------------------------------------------------------------------------

_PLANNING_PROMPT_TEMPLATE: str = """\
Sos un planificador de consultas FHIR. Tu tarea es analizar la pregunta del \
usuario y producir un plan de ejecucion estructurado.

## Grafo de referencias FHIR

Estos son los recursos disponibles y como se relacionan:

{relationships_section}

## Patrones de query disponibles

Selecciona el patron mas adecuado para la pregunta:

{patterns_section}

## Instrucciones

1. Clasifica el tipo de pregunta
2. Identifica los terminos medicos que necesitan resolucion (resolve_terminology)
3. Selecciona el patron de query mas eficiente del catalogo
4. Responde SOLO con JSON valido, sin texto adicional ni markdown

## Formato de respuesta

```json
{{
  "question_type": "count|list|aggregation|correlation|negative|temporal",
  "strategy": "<nombre del patron del catalogo>",
  "terms_to_resolve": ["termino1", "termino2"],
  "reasoning": "breve explicacion"
}}
```\
"""


def build_planning_prompt(locale_pack: LocalePack) -> str:
    """Build the planning system prompt from locale pack metadata.

    Injects the resource relationship graph and query pattern catalog
    into the prompt template.

    Args:
        locale_pack: The locale pack with FHIR knowledge.

    Returns:
        The complete planning system prompt.
    """
    # Build relationships section
    rel_lines: list[str] = []
    for rel in locale_pack.resource_relationships:
        rel_lines.append(f"- {rel.source} --{rel.search_param}--> {rel.target}")
    if not rel_lines:
        rel_lines.append("(no hay relaciones definidas)")
    relationships_section = "\n".join(rel_lines)

    # Build patterns section
    pat_lines: list[str] = []
    for pat in locale_pack.query_patterns:
        pat_lines.append(
            f"### {pat.name}\n"
            f"- Cuando: {pat.description}\n"
            f"- Template: `{pat.template}`\n"
            f'- Ejemplo: "{pat.example_question}" -> `{pat.example_query}`'
        )
    if not pat_lines:
        pat_lines.append("(no hay patrones definidos)")
    patterns_section = "\n\n".join(pat_lines)

    return _PLANNING_PROMPT_TEMPLATE.format(
        relationships_section=relationships_section,
        patterns_section=patterns_section,
    )


# ---------------------------------------------------------------------------
# Default fallback plan
# ---------------------------------------------------------------------------

_FALLBACK_PLAN = QueryPlan(
    question_type="unknown",
    strategy="search_include",
    terms_to_resolve=(),
    reasoning="Planner could not classify — falling back to general search strategy.",
    raw_json="",
)


# ---------------------------------------------------------------------------
# plan_query — the main planning function
# ---------------------------------------------------------------------------


async def plan_query(
    llm: LLMClient,
    query: str,
    locale_pack: LocalePack,
    *,
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> QueryPlan:
    """Generate a FHIR query plan for the given question.

    Makes a single LLM call with no tools.  The LLM receives the FHIR
    knowledge (resource graph + query patterns) as context and returns
    a structured JSON plan.

    Args:
        llm: LLM client for the planning call.
        query: The user's natural language question.
        locale_pack: Locale pack with FHIR knowledge.
        temperature: Sampling temperature (0.0 for deterministic).
        max_tokens: Max tokens for the planning response.

    Returns:
        A ``QueryPlan`` with question classification and strategy.
        Returns a fallback plan if the LLM output is not valid JSON.
    """
    from saludai_agent.types import Message

    system_prompt = build_planning_prompt(locale_pack)
    messages = [Message(role="user", content=query)]

    response = await llm.generate(
        system=system_prompt,
        messages=messages,
        tools=None,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw = response.content or ""
    return _parse_plan(raw)


def _parse_plan(raw: str) -> QueryPlan:
    """Parse the LLM's JSON response into a QueryPlan.

    Handles common LLM output issues: markdown code fences, extra text
    around the JSON, etc.

    Args:
        raw: Raw LLM output string.

    Returns:
        A ``QueryPlan``, or the fallback plan if parsing fails.
    """
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    # Try to find JSON object in the text
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("planner_no_json_found raw=%s", raw[:200])
        return _FALLBACK_PLAN

    json_str = cleaned[start : end + 1]

    try:
        data: dict[str, Any] = json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("planner_json_parse_error raw=%s", json_str[:200])
        return _FALLBACK_PLAN

    terms = data.get("terms_to_resolve", [])
    if isinstance(terms, str):
        terms = [terms]

    return QueryPlan(
        question_type=str(data.get("question_type", "unknown")),
        strategy=str(data.get("strategy", "search_include")),
        terms_to_resolve=tuple(str(t) for t in terms),
        reasoning=str(data.get("reasoning", "")),
        raw_json=json_str,
    )


# ---------------------------------------------------------------------------
# Format plan for injection into executor system prompt
# ---------------------------------------------------------------------------


def format_plan_for_prompt(plan: QueryPlan) -> str:
    """Format a QueryPlan as a text block for injection into the executor prompt.

    Args:
        plan: The query plan to format.

    Returns:
        A markdown-formatted plan section.
    """
    terms_str = ", ".join(plan.terms_to_resolve) if plan.terms_to_resolve else "(ninguno)"
    return (
        f"## Plan de ejecucion\n\n"
        f"- **Tipo de pregunta:** {plan.question_type}\n"
        f"- **Estrategia:** {plan.strategy}\n"
        f"- **Terminos a resolver:** {terms_str}\n"
        f"- **Razonamiento:** {plan.reasoning}\n\n"
        f"Segui este plan como guia. Si la estrategia no funciona, "
        f"podes adaptarte y usar otras herramientas."
    )


# ---------------------------------------------------------------------------
# Action Space Reduction — resolve allowed tool set from strategy
# ---------------------------------------------------------------------------


def resolve_tool_set(
    strategy: str,
    query_patterns: tuple[QueryPattern, ...],
) -> frozenset[str] | None:
    """Resolve the set of tools the executor may use for a given strategy.

    Looks up the strategy name in the query pattern catalog and returns
    the ``allowed_tools`` declared by that pattern.  This implements
    *Action Space Reduction*: the planner constrains which tools the
    executor LLM can see, forcing it to use the optimal approach.

    Args:
        strategy: Strategy name from the ``QueryPlan`` (e.g. ``"count_simple"``).
        query_patterns: Query patterns from the locale pack.

    Returns:
        A ``frozenset`` of tool names if the pattern restricts tools,
        or ``None`` if all tools are allowed (pattern has empty
        ``allowed_tools`` or strategy not found in catalog).
    """
    for pattern in query_patterns:
        if pattern.name == strategy:
            if pattern.allowed_tools:
                return frozenset(pattern.allowed_tools)
            return None  # empty tuple → all tools
    # Strategy not found in catalog — don't restrict (safe fallback)
    logger.warning("resolve_tool_set unknown strategy=%s", strategy)
    return None
