# ADR-009: Hybrid Query Planner (Plan-and-Execute)

**Status:** Accepted

## Context

The agent uses a naive ReAct loop where the LLM decides ad-hoc which tools to call. This worked well with small data (55 patients, 98% accuracy) but when scaling to 200 patients and 100 questions, accuracy dropped to 79%.

The main problem: the LLM doesn't consistently leverage advanced FHIR search capabilities (`_has`, `_summary=count`, `_include`), resulting in suboptimal queries that transfer unnecessary data and require many iterations.

We need the agent to "know" FHIR at the query planning level, not just at execution.

### Constraints

- No LangChain (ADR-002) — the planner must be part of the custom loop
- Extensible per locale (ADR-007) — FHIR knowledge can vary by country
- Auditable (Langfuse) — the plan must be traceable
- Reasonable cost — don't double LLM call spending

## Decision

Implement a **Hybrid Query Planner** with a Plan-and-Execute pattern:

1. **Planning phase**: 1 LLM call (no tools) that classifies the question and selects a strategy from a structured catalog of FHIR patterns
2. **Execution phase**: the existing ReAct loop, with the plan injected as context in the system prompt
3. **Fallback**: if the planned strategy doesn't produce results, the executor falls back to free ReAct

FHIR knowledge is modeled as structured data, not as text in the prompt:
- **Reference graph**: `ResourceRelationship` dataclass with edges between resource types
- **Pattern catalog**: ~10 validated FHIR query templates (count, search, aggregate, etc.)
- **Both injected into the planner prompt** as compact context

The LLM handles the fuzzy part (NLP classification, term extraction). The catalog handles the precise part (valid FHIR syntax, proven patterns).

### New tool: `count_fhir`

Dedicated tool for server-side counting that always adds `_summary=count`. Supports `_has` for cross-resource counts without transferring data.

### Evolution path

The design supports gradual scaling:
- Current catalog (~15 patterns) → RAG with vector store when exceeding 50 patterns
- Current graph (adjacency list) → Graph DB when exceeding 30 resource types with 4+ hop chains
- Current terminology (rapidfuzz) → Medical embeddings when exceeding 1000 concepts

## Consequences

### Positive
- Better accuracy: the agent chooses optimal queries from the start
- Lower cost: `_summary=count` avoids transferring data for ~60% of questions
- Fewer iterations: 1-2 instead of 3-5 for questions with a clear plan
- Testable: the pattern catalog is deterministic and verifiable with unit tests
- Extensible: new resource types are added to the graph, new patterns to the catalog
- Auditable: the plan (JSON) is logged in Langfuse as a separate span

### Negative
- +1 LLM call per query (~$0.01-0.03, offset by fewer iterations)
- More complexity in the loop (2 phases instead of 1)
- The catalog needs maintenance when resource types are added

### Risks
- The planner could misclassify a question → mitigated by fallback to ReAct
- The catalog might not cover a new case → mitigated by fallback to ReAct
- The incremental planner call cost might not pay off → measure in benchmark

## Alternatives Considered

### Option A: Pure LLM (everything in prompt)

All FHIR knowledge as text in the system prompt. The LLM reasons alone.

- Pros: minimal code, flexible
- Cons: LLM forgets/distorts FHIR syntax, expensive in tokens, not testable

### Option B: Pure Internal Model (rules)

Deterministic rules engine that maps questions to queries without LLM.

- Pros: deterministic, fast, zero cost
- Cons: can't classify natural language, brittle with new questions

### Option C: Full RAG + Graph DB + Vector Store

Vector store (Chroma) for patterns, Neo4j for FHIR relationships, embeddings for terminology.

- Pros: scales to thousands of patterns and terminologies
- Cons: overkill for ~15 patterns and ~170 codes, adds 3 infrastructure dependencies

## References

- Wang et al. 2023: "Plan-and-Solve Prompting"
- FHIR R4 Search: https://hl7.org/fhir/R4/search.html
- ADR-002: No LangChain
- ADR-007: Locale packs
- ADR-008: FHIR Awareness
