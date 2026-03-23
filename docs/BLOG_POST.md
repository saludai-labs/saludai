# Building a FHIR Agent from 60% to 84%: Lessons from Benchmark-Driven AI Development

*How systematic failure analysis, not prompt engineering, turned a mediocre AI agent into one that outperforms most LLMs on clinical data queries.*

---

## The Problem

If you work in public health in Latin America, querying clinical data is painful. FHIR (Fast Healthcare Interoperability Resources) is the standard, but the API is complex: chained search parameters, reference traversal across resource types, terminology codes that vary by country. A simple question like *"How many patients with type 2 diabetes over 60 are in Buenos Aires?"* requires knowing that diabetes is SNOMED code 44054006, building the right FHIR query with `_has` reverse chaining, and filtering by address-state.

We built [SaludAI](https://github.com/saludai-labs/saludai) to solve this: an AI agent that takes clinical questions in natural language and returns traceable answers from a FHIR R4 server. Open source, built and tested against Argentine synthetic data, benchmarked rigorously.

This post is about the journey from 60% accuracy to 84% — not through prompt tweaking, but through analyzing *why specific questions fail* and engineering solutions for each failure mode.

## Why an Agent, Not RAG or Fine-Tuning?

FHIR data isn't static documents — it's a live API with structured relationships. RAG doesn't work because the answer doesn't exist in a document to retrieve; it requires *executing queries* against a server. Fine-tuning doesn't work because FHIR servers have different data; the model needs to *reason* about what to query, not memorize answers.

An agent loop fits naturally: the LLM plans a query strategy, calls tools (terminology resolution, FHIR search, code execution), evaluates results, and iterates if needed. Every step is logged to [Langfuse](https://langfuse.com) for full observability.

We deliberately avoided LangChain. The agent loop is ~300 lines of Python. When a question fails, we can read every line that executed. When we add a feature, we know exactly where it goes. Framework simplicity isn't a compromise — it's a design choice that pays dividends in debugging speed.

## The Benchmark

We built a 100-question evaluation inspired by [FHIR-AgentBench](https://arxiv.org/abs/2509.19319) (Verily/KAIST/MIT), adapted for Argentine clinical data:

- **200 synthetic patients** with Argentine names, DNIs, 18 provinces
- **3,182 FHIR resources** across 10 types (Patient, Condition, Observation, MedicationRequest, Encounter, Procedure, DiagnosticReport, AllergyIntolerance, Immunization, CarePlan)
- **4 terminology systems**: SNOMED CT (Argentine edition), CIE-10, LOINC, ATC
- **3 difficulty levels**: Simple (demographics, counting), Medium (terminology + filters), Complex (multi-hop, aggregation, temporal)
- **Hybrid judge**: programmatic numeric range checking + LLM-as-judge for semantic evaluation

Every question has a ground truth answer computed directly from the seed data. The judge is deterministic for numeric answers (no LLM involved) and uses Claude Haiku only for semantic comparison.

## The Curve: Every Fix Was a Specific Failure

Here's the accuracy evolution across 17 experiments. Each jump came from analyzing *individual failing questions*, not from blanket changes.

### Experiment 1 → 2: Pagination (+22pp, 60% → 82%)

**Root cause:** Our FHIR client set `_count=200` and returned only the first page. With 200 patients generating 687 immunizations, 437 encounters, and 361 medication requests, most aggregation queries returned truncated data.

**Fix:** `search_all()` — automatic pagination that follows `next` links in FHIR bundles. Simple, but it immediately fixed 11 questions.

**Lesson:** Before optimizing the AI, make sure it *sees all the data*.

### Experiment 2 → 4: Code Interpreter (+12pp, 82% → 94%)

**Root cause:** Questions requiring computation — averages, percentages, date calculations, set intersections — forced the LLM to do arithmetic in its head. It's bad at this.

**Fix:** `execute_code` tool — a sandboxed Python environment where the agent writes and runs code. The last search results are automatically injected as the `entries` variable.

The agent now writes `len([e for e in entries if ...])` instead of trying to count mentally. For complex intersections like *"patients with condition X AND medication Y"*, it computes set intersections in Python.

**Lesson:** Let LLMs reason about *what* to compute, not *how* to compute it. Give them a calculator.

### Experiment 6: The Humbling (94% → 79%)

We expanded from 50 questions / 55 patients to 100 questions / 200 patients / 10 resource types. Accuracy dropped 15 points. This was the most valuable experiment — it revealed that our 94% was fragile.

New failure modes:
- Agent using `search_fhir` for counting instead of server-side `_summary=count`
- Context windows exploding with 687 immunization records
- New resource types (CarePlan, Procedure) with relationships the agent didn't understand

### Experiment 6 → 7: Query Planner (+10pp, 79% → 89%)

**Root cause:** The agent was using a purely reactive loop (ReAct). For complex questions requiring 3-4 resource traversals, it would start querying without a plan and get lost.

**Fix:** A Hybrid Query Planner (plan-and-execute pattern):

1. A lightweight FHIR knowledge graph: 10 resource relationships, 11 query patterns
2. Before the agent loop starts, the planner classifies the question and selects a strategy
3. The strategy includes which tools to use (Action Space Reduction — the agent literally cannot see irrelevant tools)
4. The plan is injected into the system prompt as context

This is more effective than prompt suggestions. Instead of saying "you should use count_fhir," we *remove* `search_fhir` from the tool list for counting questions. The LLM can't misuse what it can't see.

**Lesson:** Plan-and-Execute > ReAct for structured domains. When the problem space is well-defined (FHIR has a finite set of resources and relationships), a planner with domain knowledge beats a general-purpose reasoning loop.

### Experiment 7 → 8: Cost Optimization (-33% cost, same accuracy)

We analyzed token usage and found that the system prompt (~4,300 tokens) was repeated in every iteration across all 100 questions — $5.26 of the $8.66 total cost.

**Fixes:**
- Prompt caching (Anthropic's cache_control) — the system prompt is cached and reused
- System prompt diet — removed redundant instructions, compressed examples

Result: cost per query dropped from $0.089 to $0.060 with no accuracy loss. Prompt caching alone saved 49%.

## Multi-LLM Results

We ran all 100 questions through 5 different LLMs with identical agent infrastructure:

| Model | Accuracy | Simple | Medium | Complex | Errors |
|-------|----------|--------|--------|---------|--------|
| **Claude Sonnet 4.5** | **84.0%** | 94% | 93% | 72% | 8 |
| Claude Haiku 4.5 | 77.0% | 100% | 80% | 65% | 7 |
| GPT-4o | 63.0% | 100% | 73% | 40% | 3 |
| Llama 3.3 70B | 48.0% | 94% | 63% | 16% | 9 |
| Qwen 3.5 9B | 25.0% | 50% | 29% | 12% | 1 |

Key observations:

1. **Simple questions are solved.** Every model above 9B scores 94-100% on basic demographics and counting. This is a commodity capability.

2. **Complex questions separate models.** Multi-hop reference traversal (Patient → Condition → MedicationRequest) and set operations (intersection of patients with X AND Y) require sustained reasoning across 3-5 tool calls. Only Sonnet handles this reliably.

3. **Errors are mostly max_iterations.** Most "errors" aren't crashes — the agent runs out of iteration budget (8 steps) on complex multi-hop queries. With more budget, accuracy would be higher but cost increases proportionally.

4. **The agent infrastructure matters as much as the model.** Our planner, tool design, and action space reduction are what make Sonnet hit 84% instead of the ~60% you'd get with a naive ReAct loop.

## What We Learned

**1. Benchmark everything, trust nothing.** The gap between "it seems to work" and "it works on 100 diverse questions" is enormous. Our first "88% accuracy" was on 25 easy questions with 2 resource types. The honest baseline was 60%.

**2. Analyze failures per question, not averages.** "82% accuracy" tells you nothing. "11 failures are truncated data, 4 are wrong terminology codes, 3 are arithmetic errors" tells you exactly what to fix.

**3. Tool design > prompt engineering.** Adding `execute_code` was worth +12pp. Adding `count_fhir` (server-side counting) fixed an entire class of token-explosion problems. No amount of prompt tweaking achieves this.

**4. Domain knowledge in the agent, not just the LLM.** The query planner with FHIR resource relationships outperforms telling the LLM "FHIR has these resources." Structured knowledge beats natural language instructions.

**5. One fix for one model can break another.** Schema flattening fixed GPT-4o (Simple: 53% → 100%) but broke Qwen (29% → 13%). Every change to tool definitions must be validated across all target models.

## Try It

```bash
git clone https://github.com/saludai-labs/saludai.git
cd saludai && uv sync
docker compose up -d
uv run saludai query "¿Cuántos pacientes tienen diabetes tipo 2?"
```

SaludAI is open source (Apache 2.0), built for Argentina's health system with an architecture designed to extend across Latin America. Module 1 (FHIR Smart Agent) is complete. We're planning Module 2 (Document Intelligence — OCR + NER for clinical documents → FHIR).

If you work in health tech in LATAM, or if you're building AI agents for structured domains, we'd love to hear from you. [GitHub](https://github.com/saludai-labs/saludai) | [Issues](https://github.com/saludai-labs/saludai/issues) | [Discussions](https://github.com/saludai-labs/saludai/discussions)

---

*Built by [Federico](https://github.com/saludai-labs) with Claude Code. 694 tests, 93.67% coverage, 10 architecture decision records, 17 experiments logged.*
