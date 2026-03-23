# ADR-002: No LangChain — Custom Agent Loop

**Status:** Accepted

## Context

To implement the FHIR Smart Agent, we need an agent loop that orchestrates LLM calls, tool execution, and multi-turn reasoning. Popular frameworks (LangChain, LlamaIndex, CrewAI) offer abstractions for this.

However, SaludAI operates in the clinical domain where **auditability** and **traceability** of every agent decision are non-negotiable requirements. We need full control over:
- What is sent to the LLM in each iteration
- How tool results are processed and validated
- What is logged and traced in Langfuse
- How errors and retries are handled

## Decision

Implement a **custom agent loop** in `saludai-agent` without depending on LangChain, LangGraph, LlamaIndex, CrewAI, or any agent framework.

The loop uses **native tool calling** from the LLM provider (Anthropic/OpenAI) directly, with a custom `LLMClient` abstraction that is provider-agnostic.

## Consequences

### Positive
- **Full auditability:** every step of the loop is our own code, inspectable and testable
- **Traceability:** explicit Langfuse instrumentation — each generation, tool call, and decision has its own span
- **No opaque abstractions:** no "chains," "runnables," or magic "agents" between our code and the LLM
- **True provider-agnostic:** our `LLMClient` interface supports Anthropic, OpenAI, and Ollama without third-party adapters
- **Simple testing:** the loop is a standard Python class, tested with direct mocks
- **No transitive dependencies:** LangChain brings ~50 dependencies; our agent has ~5
- **Free evolution:** we can change the loop architecture without waiting for framework releases

### Negative
- **More custom code:** the agent loop, tool registry, and message handling are ~500 lines of our own code
- **No plugin ecosystem:** we can't use "LangChain tools" or "LangChain retrievers" directly
- **Internal documentation needed:** we must document our own loop well for new contributors

### Risks
- If agent complexity grows significantly (multi-agent, planning, etc.), maintaining the custom loop may become costly
- Mitigation: the modular design (LLMClient, ToolRegistry, Tracer) allows refactoring without rewriting everything

## Alternatives Considered

### Option A: LangChain / LangGraph
- Pros: large ecosystem, many examples, native LangSmith integration
- Cons: heavy and opaque abstractions, ~50 transitive dependencies, frequent breaking changes, hard to debug, LangSmith lock-in for tracing

### Option B: LlamaIndex
- Pros: good RAG and query engine support
- Cons: oriented toward RAG/search, not agent loops with FHIR tools; equally opaque abstractions

### Option C: CrewAI
- Pros: native multi-agent, roles/tasks
- Cons: overkill for a single agent, internal LangChain dependency, less control over prompts

### Option D: Custom (chosen)
- Pros: full control, minimal dependencies, auditability, simple testing
- Cons: more custom code to maintain

## Re-evaluation: Should we migrate to LangGraph?

**Verdict:** No. The decision stands.

### Context

Over time, the agent loop accumulated several extensions that LangGraph offers as first-class primitives:

| Feature | Our code | LangGraph equivalent |
|---------|----------|---------------------|
| ReAct loop | `loop.py` (~200 loc) | `create_react_agent()` |
| Working memory | `store` dict (10 loc) | `StateGraph` with `TypedDict` |
| Plan-and-Execute | `planner.py` (~150 loc) | `PlanExecute` pattern |
| Action Space Reduction | Tool filtering (~30 loc) | Conditional edges + tool nodes |
| Tracing | Langfuse protocol (~100 loc) | LangSmith native or callbacks |
| Checkpointing/resume | Manual JSONL (~50 loc) | `SqliteSaver` / `PostgresSaver` |

Total custom: **~500 loc**. Each piece is individually simple (<50 lines), testable in isolation, and understandable in 2 minutes.

### Why NOT migrate

**1. Real complexity vs perceived complexity**

The question "shouldn't we use LangGraph?" arises when looking at the list of custom features. But the real complexity of each one is low:

- `store` = 10 lines (a dict + injection into globals)
- Planner = 1 LLM call returning JSON, no orchestration
- ASR = filtering a list of tools based on the plan
- Tracing = protocol with 5 methods, ~40 loc each

LangGraph would solve all of this, but in exchange introduces:
- A graph with nodes, edges, conditional routing, state reducers
- Concepts like `Channels`, `Reducers`, `Checkpoints`
- Dependency on `langchain-core` (~50 transitive deps)

It's trading **accidental** complexity (our 500 loc) for **essential** complexity of the framework (learning, maintaining, and debugging a state graph). For a single ReAct agent, it's overkill.

Ref: Brooks (1986) "No Silver Bullet" — the distinction between essential and accidental complexity.

**2. Auditability in clinical context**

The original ADR-002 argument not only still holds — it's reinforced. With the extensions (planner, ASR, store), each piece has direct unit tests, structured logs, and Langfuse traces with line-level granularity. In LangGraph, debugging goes through inspecting graph state, adding a layer of indirection.

For a system that processes clinical data, "I can read every line of code that touches my data" is a feature, not a bug.

**3. Dependency stability**

The LangChain ecosystem has a history of frequent breaking changes (v0.1 → v0.2 → v0.3 in ~12 months, each with API changes). For a project on PyPI used by third parties, pinning a volatile dependency is risky.

Our core dependencies (`httpx`, `pydantic`, `langfuse`) have stable APIs with real semantic versioning.

**4. The "if I can write it in a day, I don't need a framework" rule**

Each extension took 1-2 hours. The cumulative total is ~1 day of work. LangGraph would take ~1 day of setup + learning + migration, and then we'd be tied to the framework forever.

### When we WOULD migrate

The decision reverses if the project needs any of these:

- **Multi-agent**: specialized agents that collaborate
- **Human-in-the-loop**: clinical approval before executing actions
- **Long-running workflows**: tasks lasting hours with robust checkpointing
- **Complex conditional branching**: >3 execution paths with backtracking

In that case, LangGraph's state graph would justify its complexity. But that's a future problem, not a present one.

Ref: YAGNI (Beck, 1999) — "You Aren't Gonna Need It."

---

## References

### Code
- `packages/saludai-agent/src/saludai_agent/loop.py` — agent loop (~200 loc)
- `packages/saludai-agent/src/saludai_agent/llm.py` — LLMClient protocol + providers
- `packages/saludai-agent/src/saludai_agent/tools.py` — ToolRegistry + store
- `packages/saludai-agent/src/saludai_agent/planner.py` — Query Planner

### APIs and frameworks
- [Anthropic tool use docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [OpenAI function calling docs](https://platform.openai.com/docs/guides/function-calling)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/) — for reference of what we don't use and why

### Theory
- Brooks (1986) "No Silver Bullet — Essence and Accident in Software Engineering"
- Beck (1999) "Extreme Programming Explained" — YAGNI principle

### Related ADRs
- ADR-009: Hybrid Query Planner
- ADR-010: Scratchpad Working Memory
