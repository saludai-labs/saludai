# SaludAI — Architecture

## Overview

SaludAI is a modular FHIR reasoning agent built as independent Python packages. Design priorities:

1. **Auditability** — every agent step is traced via Langfuse
2. **Accuracy over speed** — systematic failure analysis over prompt tuning
3. **Modularity** — each package works independently
4. **Extensibility** — locale packs enable country-specific terminology and prompts

## Stack

```
Python 3.12+ · UV workspaces · Ruff · Pytest
httpx (async FHIR client) · fhir.resources (Pydantic models)
Anthropic/OpenAI/Ollama (provider-agnostic LLM layer)
Langfuse (observability) · FastAPI (REST) · MCP SDK (Claude Desktop)
HAPI FHIR R4 (Docker) · pydantic-settings (config)
```

## Packages

```
saludai-core     FHIR client, terminology resolver, query builder, locale packs
saludai-agent    Agent loop, query planner, tools, LLM abstraction
saludai-mcp      MCP server (Claude Desktop, Cursor, etc.)
saludai-api      FastAPI REST interface
```

`saludai-core` has no internal dependencies. All others depend on it.

## Agent Loop

~300 lines of Python. No framework (no LangChain). The loop follows a plan-execute-evaluate cycle:

```
User Question
     │
     ▼
[Query Planner] ── 1 LLM call, classifies question, selects FHIR strategy
     │
     ▼  QueryPlan injected into system prompt
[Agent Loop] ── ReAct loop with plan-aware tool selection
     │  Tools: resolve_terminology, search_fhir, count_fhir,
     │         get_resource, execute_code
     │  Max iterations: 12 (configurable)
     │  Working memory: persistent store across iterations
     │
     ▼
AgentResult (answer + sources + trace URL)
```

### Query Planner (ADR-009)

FHIR knowledge modeled as structured data, not prompt text:

- **Resource graph** (`ResourceRelationship`): edges between resource types with search params. Derives `_include`, `_revinclude`, `_has` patterns automatically.
- **Query pattern catalog** (`QueryPattern`): validated FHIR query templates with allowed tool sets (action space reduction).
- Both live in the locale pack — extensible per country.

The LLM handles the fuzzy part (NLP classification, term extraction). The catalog handles the precise part (valid FHIR syntax, proven patterns).

### Tools

| Tool | Purpose |
|------|---------|
| `resolve_terminology` | Natural language → SNOMED CT / CIE-10 / LOINC / ATC codes (fuzzy matching via rapidfuzz) |
| `search_fhir` | FHIR search with auto-pagination, `_include`/`_revinclude`, smart summary for large results |
| `count_fhir` | Server-side counting via `_summary=count`, supports `_has` for cross-resource counts |
| `get_resource` | Direct resource lookup by reference |
| `execute_code` | Sandboxed Python for aggregation, filtering, calculations |

### Action Space Reduction

Instead of suggesting tools via prompt, irrelevant tools are **removed** from the LLM's context based on the query plan. The model can't misuse what it can't see.

## Locale Packs

Country-specific bundles of terminology, prompts, and FHIR metadata:

```python
from saludai_core import load_locale_pack

pack = load_locale_pack("ar")  # Argentina (built-in)
# SNOMED CT AR + CIE-10 AR + LOINC + ATC
# Spanish system prompt + tool descriptions
# FHIR resource relationships + query patterns
```

See `docs/LOCALE_GUIDE.md` for creating new packs.

## Observability

Every agent run is fully traced in Langfuse:
- Query plan generation
- Each iteration: LLM call, tool selection, tool execution, result
- Token usage and cost per step
- Final answer with evaluation

## LLM Abstraction

Provider-agnostic via `LLMClient` protocol. Same agent loop works with Claude, GPT-4o, Llama, or Qwen. Selection via `SALUDAI_LLM_PROVIDER` env var.

## Infrastructure

```yaml
# docker-compose.yml
services:
  hapi-fhir:   # FHIR R4 server (H2 in-memory, ephemeral)
  fhir-seed:   # Loads 200 synthetic Argentine patients on startup
```

Langfuse Cloud (free tier) for observability — no local containers needed.

## ADR Index

| ADR | Decision |
|-----|----------|
| [001](decisions/001-monorepo-uv-workspaces.md) | Monorepo with UV workspaces |
| [002](decisions/002-no-langchain.md) | No LangChain — custom agent loop |
| [003](decisions/003-python-first-polyglot.md) | Python as primary language |
| [004](decisions/004-langfuse-observability.md) | Langfuse for observability |
| [005](decisions/005-fhir-r4-only.md) | FHIR R4 only |
| [006](decisions/006-langfuse-cloud.md) | Langfuse Cloud for development |
| [007](decisions/007-locale-packs.md) | Locale pack system |
| [008](decisions/008-fhir-awareness-locale-packs.md) | FHIR awareness metadata in locale packs |
| [009](decisions/009-hybrid-query-planner.md) | Hybrid query planner |
| [010](decisions/010-scratchpad-working-memory.md) | Scratchpad and working memory |
| [011](decisions/011-multi-llm-tool-compatibility.md) | Multi-LLM tool compatibility |
