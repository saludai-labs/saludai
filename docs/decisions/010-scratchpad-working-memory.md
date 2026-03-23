# ADR-010: Scratchpad Working Memory for the Agent Loop

**Status:** Accepted

## Context

### The problem: re-querying in cross-resource queries

The agent loop uses a scratchpad `entries` containing the FHIR resources from the **last** search. When a question requires crossing data from 2+ searches (e.g., "patients with DM2 who have glucose > 140"), the agent loses results from the first search when performing the second because `entries` is overwritten.

This causes a **re-querying** pattern: the agent repeats the same FHIR queries multiple times to recover data it already had. Evidence from benchmarks:

| Question | Iterations | Problem |
|----------|-----------|---------|
| C10 (DM2 + glucose > 140) | 10 | Re-queries Conditions 3x, Observations 2x |
| C45 (HTN + BP > 140 in BA) | 12 | Re-queries Conditions 3x, Observations 2x |
| C05 (under 18 + conditions) | 12 (max, failure) | Can't cross age + conditions |
| C30 (DM2 without HbA1c) | 12 (max, failure) | Can't do cross-resource negation |

Re-queries represent ~60% of cost in cross-resource queries ($0.10+ per question vs $0.02-0.05 for simple queries). Two questions directly fail due to max_iterations because the agent enters a loop of search → lose data → search again.

---

## Theoretical Framework: Memory in LLM Agents

### Memory taxonomy in agents

The LLM agents literature distinguishes several memory types, by analogy with cognitive psychology (Atkinson & Shiffrin, 1968):

| Type | Cognitive analogy | In LLM agents | In SaludAI |
|------|------------------|---------------|------------|
| **Sensory memory** | Sensory buffer | Current token window | User input |
| **Short-term / Working memory** | Active manipulation | Scratchpad, notepad | `entries` + `store` |
| **Long-term memory** | Durable storage | Vector stores, RAG | Terminology CSVs, FHIR knowledge graph |
| **Episodic memory** | Event recollection | Conversation history | Message history in the loop |
| **Semantic memory** | General knowledge | Model weights | FHIR knowledge in the LLM |
| **Procedural memory** | Know-how | System prompt, tools | Prompt + tool definitions |

Ref: Park et al. (2023) "Generative Agents: Interactive Simulacra of Human Behavior"

### The Scratchpad pattern

**Scratchpad Memory** (Nye et al., 2021 — "Show Your Work: Scratchpads for Intermediate Computation with Language Models") demonstrated that giving an LLM an intermediate writing space significantly improves its multi-step reasoning ability. In their study, arithmetic tasks the model failed were solved correctly when it could write intermediate steps.

Key insight: **the LLM's context window is like human working memory — limited**. If an intermediate step is lost (by overwriting or falling out of context), the model must recalculate from scratch. An explicit scratchpad allows "externalizing" intermediate results.

### Our variant: Tool-Scoped Working Memory

We implement a specific variant combining two memory levels:

```
┌─────────────────────────────────────────────────────┐
│  Agent Run (1 user question)                        │
│                                                     │
│  ┌─ Iteration 1 ─────────────────────────────────┐  │
│  │  search_fhir → entries = [Conditions...]      │  │
│  │  execute_code → store['dm2'] = set(...)       │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌─ Iteration 2 ─────────────────────────────────┐  │
│  │  search_fhir → entries = [Observations...]    │  │  ← entries overwritten
│  │  execute_code → store['dm2'] still alive!     │  │  ← store persists
│  │               → result = store['dm2'] & obs   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  store is reset at the end of the run               │
└─────────────────────────────────────────────────────┘
```

| Variable | Type | Lifetime | Semantics | Analogy |
|----------|------|----------|-----------|---------|
| `entries` | list | Last search | Result cache (overwritten) | Sensory register |
| `store` | dict | Entire execution | Accumulative memory (agent decides what to save) | Working memory |
| message history | list | Entire execution | Step history | Episodic memory |

The key difference from LangGraph State: our `store` is **opaque** — the framework doesn't know what's inside, only the agent decides what to save. In LangGraph, state is typed and the framework can do merge/reduce. We chose the opaque version because it's simpler and the agent only needs to save sets of IDs between searches, not complex structured state.

---

## Decision

Add a persistent **`store` dict** to `ToolRegistry` that is injected into `execute_code` alongside `entries`. The agent can save intermediate results between searches without re-querying.

### Usage example

```python
# Iteration 1: search Conditions, save patient IDs
search_fhir("Condition", {"code": "...", "_include": "Condition:subject"})
execute_code("store['dm2_patients'] = set(e['subject']['reference'] "
             "for e in entries if e.get('resourceType') == 'Condition')")

# Iteration 2: search Observations (entries overwritten, store is not)
search_fhir("Observation", {"code": "...", "_include": "Observation:subject"})
execute_code("obs_patients = set(e['subject']['reference'] for e in entries); "
             "result = store['dm2_patients'] & obs_patients; "
             "print(len(result))")
```

## Consequences

### Positive
- Eliminates re-querying: cross-resource queries go from 10-12 iterations to ~4-5
- Reduces cost ~50-60% for correlation/negation questions
- Unblocks questions that previously failed due to max_iterations
- Zero-cost for simple queries (store stays empty, unused)
- No changes to `loop.py` or the Tracer protocol — only touches `ToolRegistry`

### Negative
- The agent must learn to use `store` via prompt — it's not automatic
- Adds one more variable to the `execute_code` sandbox

### Risks
- The agent might not use `store` if the prompt isn't clear enough. Mitigation: the tool description also mentions it, and the planner can suggest the pattern for multi_search queries.
- Data accumulation in `store` could use memory in long queries. Mitigation: store is reset between queries (each question creates a new ToolRegistry).

---

## Alternatives Considered

### Option A: Entries history (automatic stack)
Each `search_fhir` pushes to a stack: `entries_history = [entries_0, entries_1, ...]`.
- Pros: requires no agent action — all search results accumulate
- Cons: agent doesn't know what each entry contains, grows without control, injects irrelevant data into context. Breaks the cognitive analogy: working memory should be selective, not indiscriminately accumulative (Cowan, 2001).

### Option B: Auto-named variables (entries_1, entries_2, ...)
Each search creates a new variable with an incremental suffix.
- Pros: automatic, no prompt engineering
- Cons: agent doesn't know how many exist or what each contains. Fragile to order changes. The LLM would need to "explore" available variables.

### Option C: LangGraph typed State
Migrate to LangGraph and model state as `TypedDict`.
- Pros: first-class pattern, automatic merge/reduce, checkpointing
- Cons: adopting an entire framework to solve a 10-line problem. See ADR-002 for the full discussion on frameworks vs custom.

### Option D: Explicit store dict (CHOSEN)
Opaque dict, the agent decides what to save and with what key.
- Pros: minimal overhead (10 loc), clear semantics, the agent has agency over its own working memory. Aligned with Nye et al.'s principle: the model is better when it decides what to note down.
- Cons: requires prompt guidance.

---

## References

### Papers
- Nye et al. (2021) "Show Your Work: Scratchpads for Intermediate Computation with Language Models" — arXiv:2112.00114
- Yao et al. (2022) "ReAct: Synergizing Reasoning and Acting in Language Models" — arXiv:2210.03629
- Schick et al. (2023) "Toolformer: Language Models Can Teach Themselves to Use Tools" — arXiv:2302.04761
- Park et al. (2023) "Generative Agents: Interactive Simulacra of Human Behavior" — arXiv:2304.03442
- Sumers et al. (2023) "Cognitive Architectures for Language Agents" — arXiv:2309.02427
- Cowan (2001) "The magical number 4 in short-term memory" — Behavioral and Brain Sciences

### Frameworks
- LangGraph State: https://langchain-ai.github.io/langgraph/concepts/low_level/#state

### Code
- `packages/saludai-agent/src/saludai_agent/tools.py` — `ToolRegistry._store`
- `packages/saludai-core/src/saludai_core/locales/ar/_prompt.py` — `store` guidance
- ADR-002: No LangChain
- ADR-009: Hybrid Query Planner
