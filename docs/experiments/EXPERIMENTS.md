# SaludAI — Experiments Document

> Formal record of the experimental strategy for the FHIR Smart Agent.
> Each experiment documents hypotheses, methodology, results, and conclusions.

## Context

SaludAI evaluates its FHIR agent against a benchmark inspired by [FHIR-AgentBench](https://arxiv.org/abs/2509.19319) (Verily/KAIST/MIT, [repo](https://github.com/glee4810/FHIR-AgentBench)), adapted for Argentine clinical data. The goal is to measure progressive improvements in accuracy, resource coverage, and multi-turn capability.

### Synthetic Data

Evaluation data is generated with `data/seed/generate_seed_data.py` (deterministic seed `random.seed(42)`):

| Version | Patients | Conditions | Observations | MedicationReq | Encounters | Procedure | Allergy | Immunization | DiagReport | Total |
|---------|-----------|------------|--------------|---------------|------------|-----------|---------|-------------|------------|-------|
| v1 | 55 | ~76 | — | — | — | — | — | — | — | ~131 |
| v2 | 55 | 80 | 163 | 116 | 122 | — | — | — | — | 536 |
| v3 | 200 | 302 | 375 | 361 | 437 | ~200 | ~58 | ~687 | ~120 | 3182 |

**Demographics:** Argentine names, DNI, 18 provinces weighted by population, SNOMED CT (AR edition), ICD-10.

### Evaluation Methodology

- **Hybrid LLM-as-judge:** Programmatic pre-check for numeric ranges (deterministic, no LLM cost) + Claude Haiku as fallback for semantic evaluation. Replaces the pure LLM-as-judge from Exp 0.
- **Scoring:** 1 (correct) or 0 (incorrect). No partial scoring.
- **Determinism:** `temperature=0` on the agent under evaluation.
- **Independence:** Each question is executed with a clean agent (no prior context).
- **Categories:** `simple` (counting, demographics), `medium` (terminology, filters, status), `complex` (multi-resource, aggregation, reference traversal).

---

## Exp 0 — Inflated Baseline

### Hypothesis
The agent can answer basic questions about Patient and Condition using tool calling.

### Setup
- **Dataset:** 25 questions (8 simple, 10 medium, 7 complex)
- **Data:** 55 Patient + ~76 Condition (only 2 resource types)
- **Model:** Claude Sonnet 4.5
- **Agent:** Loop v1 with 3 tools (search_patients, search_conditions, get_resource)

### Results

| Model | Accuracy | Simple | Medium | Complex | Avg Duration |
|--------|----------|--------|--------|---------|-------------|
| Claude Sonnet 4.5 | **88.0%** | 7/8 (88%) | 10/10 (100%) | 5/7 (71%) | 13.6s |

### Analysis
The 88% is **deceptively high** for three reasons:

1. **Only 2 resource types:** All questions are resolved with Patient + Condition. The agent doesn't need to navigate Observation, MedicationRequest, or Encounter.
2. **Wide acceptance ranges:** Many questions accept ranges like "15-30" when the actual value is 22. The judge approves imprecise answers.
3. **Simple questions dominate:** 72% of questions (18/25) require 1-2 tool calls. Only 7 are genuinely complex.
4. **No cross-resource queries:** No question requires correlating data across >=3 resource types.

### Conclusion
This baseline is not useful for measuring real improvements. A more demanding benchmark is needed.

---

## Exp 1 — Honest Baseline

### Hypothesis
With enriched data (5 resource types) and harder questions (50 total, including cross-resource and aggregation), the agent's accuracy will drop to ~40-55% with Sonnet, revealing the true limitations.

### Setup
- **Dataset:** 50 questions (8 simple, 20 medium, 22 complex)
- **Data:** 55 Patient + 80 Condition + 163 Observation + 116 MedicationRequest + 122 Encounter (536 total)
- **Agent model:** Claude Sonnet 4.5
- **Judge:** Claude Haiku 4.5 (hybrid: programmatic pre-check for ranges + LLM for semantics)
- **Agent:** Loop v1 (no changes from Exp 0)
- **New subcategories:** observation_query, medication_query, encounter_query, cross_resource, calculation, reference_traversal, advanced_aggregation

### Results

| Model | Accuracy | Simple (8) | Medium (20) | Complex (22) | Avg Duration | Avg Iterations |
|--------|----------|------------|-------------|--------------|-------------|----------------|
| Claude Sonnet 4.5 | **60.0%** | 4/8 (50%) | 12/20 (60%) | 14/22 (64%) | 13.8s | 2.9 |
| Claude Haiku 4.5 | — | — | — | — | — | — |

*Judge: Claude Haiku 4.5 (with programmatic pre-check for numeric ranges).*

### Analysis

The 60% confirms that the benchmark is significantly more demanding than Exp 0:

1. **Pagination is the main blocker:** The 4 failed simple questions (S01, S02, S03, S05) fail because the agent only sees the first 20 FHIR results (default page size). It doesn't use `_summary=count` or pagination. This also affects medium and complex queries that depend on total counts.

2. **Complex surprisingly strong (64%):** The agent handles multi-step queries well: resolves terminology, uses `_include`, crosses resources. Failures in complex are due to pagination or max iterations exceeded, not reasoning inability.

3. **Medium affected by pagination (60%):** Questions like M11 (glucose count), M13 (BP), M14 (metformin), M15 (prescriptions by medication) fail because the agent doesn't see all results.

4. **Hybrid judge works well:** The programmatic pre-check for numeric ranges solved Haiku's problem of not respecting ranges. Of 50 evaluations, ~25 used the pre-check and ~25 the LLM judge.

**Failure patterns:**
- **Pagination** (~40% of failures): Agent reports 20 instead of N>20
- **Max iterations** (~10% of failures): Agent runs out of steps on complex medication queries
- **Partial data** (~50% of failures): Agent sees partial page and draws wrong conclusions

### Conclusion

60% is an honest and actionable baseline. The most impactful improvement will be implementing pagination/`_summary=count` — this should cover ~50% of current failures, potentially reaching ~75-80%.

---

## Exp 2 — Progressive Improvement

### Hypothesis
Each session will improve accuracy in the categories it addresses:
- Pagination/multi-turn: Improvement in complex queries requiring multiple steps
- Reference navigation: Improvement in cross-resource and reference traversal
- Code interpreter: Improvement in calculations and advanced aggregation
- Prompt optimization: General improvement through better prompting

### Setup
- **Dataset:** 50 questions (same as Exp 1)
- **Model:** Claude Sonnet 4.5
- **Measurement:** After each session, re-run the complete benchmark

### Progressive Results

| Session | Accuracy | Simple | Medium | Complex | Delta vs Exp 1 |
|--------|----------|--------|--------|---------|----------------|
| Pagination | **82.0%** | 8/8 (100%) | 16/20 (80%) | 17/22 (77%) | **+22pp** |
| Reference nav | **86.0%** | 8/8 (100%) | 19/20 (95%) | 16/22 (73%) | **+26pp** |
| Code interpreter | **94.0%** | 8/8 (100%) | 19/20 (95%) | 20/22 (91%) | **+34pp** |
| Judge fix + timeout | **98.0%** | 8/8 (100%) | 20/20 (100%) | 21/22 (95%) | **+38pp** |

### Analysis — Pagination

**Changes implemented:**
1. `execute_search_fhir()` injects `_count=200` by default
2. `format_bundle_summary()` handles `_summary=count` (total without entries)
3. System prompt with "Query strategy" section — guides when to use `_summary=count`
4. Tool description mentions `_summary` and `_count` as special parameters

**Impact by category:**
- **Simple 100%:** All 4 questions that failed due to pagination (S01-S03, S05) now pass thanks to `_summary=count`
- **Medium 80%:** 4 questions recovered. M02 still fails (resolve "hipertension arterial" -> SNOMED 38341003 doesn't exist in seed, the correct code is 59621000). M09 fails (list of frequent conditions — requires manual aggregation).
- **Complex 77%:** 3 questions recovered (C14, C17, C18). Remaining failures: C20 (encounter distribution by province — geographic aggregation), C21 (most prescribed medication — count aggregation).
- **4 errors:** API retries/timeouts (Anthropic rate limiting) — not related to agent logic

**Remaining failure patterns:**
- **Terminology mismatch (M02):** "hipertension arterial" resolves to 38341003 (not in seed) instead of 59621000
- **Aggregation without code interpreter (~3 failures):** Manual counting/ranking on large result sets (M09, C20, C21)
- **API instability (4 errors):** Anthropic rate limiting causes timeouts

### Analysis — Reference Navigation

**Changes implemented:**
1. Fix terminology disambiguation: display of `38341003` "Hipertension arterial" -> "Hipertension arterial sistemica" (avoids exact-match with 59621000)
2. New tool `get_resource` for individual resource reading by type and ID
3. `agent_max_iterations` from 5 to 8 (multi-medication queries need more rounds)
4. System prompt v1.2 with `_include`/`_revinclude` and medication guidance

**Impact by category:**
- **Medium 95%:** M02 (hypertension) and M19 (antihypertensives) now pass. Only M09 (aggregation) still fails.
- **Complex 73%:** C04, C08, C09 (cascade from the terminology bug + max iterations) now pass. But C07 and C18 flipped to INCORRECT due to LLM non-determinism.
- **0 errors:** The bump of max_iterations eliminated the 4 errors from Exp 2 (M14, M19, C04, C09).

**Remaining failure patterns (7):**
- **Aggregation without code interpreter (M09, C20, C21):** The LLM cannot correctly count/group 100+ records in context -> needs Code Interpreter
- **Cross-resource join with counting (C03, C05):** The LLM fails crossing Patient addresses with Condition results when there are many records
- **Non-determinism (C07, C18):** These questions pass/fail between runs — the LLM sometimes miscounts complex data

### Analysis — Code Interpreter

**Changes implemented:**
1. New tool `execute_code` — Python sandbox with restricted builtins, 5s timeout, pre-imported modules (json, collections, datetime, math, statistics, re)
2. `_restricted_import()` — whitelist of allowed modules (blocks os, subprocess, etc.)
3. System prompt v1.3 with "Data processing" section — rule to use execute_code for >10 resources

**Impact by category:**
- **Complex 91%:** Massive jump from 73% -> 91%. M09 (frequent conditions), C03, C07, C18, C20 (encounter distribution), C21 (most prescribed medication) now pass thanks to Counter/aggregation via code.
- **Medium 95%:** Stable. M07 flipped to INCORRECT due to non-determinism.
- **Simple 100%:** No changes.

**Remaining failure patterns (3):**
- **Non-determinism (M07, C14):** Pass/fail between runs — the LLM sometimes misinterprets complex data
- **Timeout (C05):** Complex query with large data exceeds 120s

### Analysis — Judge Fix

**Changes implemented:**
1. Judge regex fix: new pattern for bare `X-Y` ranges (without "Range:" prefix) — matches notes like `"Active: 58-66"`
2. Judge regex fix: tolerance for `%` in patterns `between X% and Y%` — matches notes like `"Accept between 83% and 93%"`
3. Timeout bump: `question_timeout_seconds` from 120 to 180
4. 5 new tests for the corrected patterns

**Impact by category:**
- **Medium 100%:** M07 now passes — the judge correctly detects that the agent's answer is in the range `58-66`
- **Complex 95%:** C14 now passes — the judge correctly parses `"between 83% and 93%"` with `%`
- **Simple 100%:** No changes.

**Remaining failure (1):**
- **Max iterations (C05):** Complex query exceeds 8 iterations (not timeout, but iteration limit)

### Final Target
- **Accuracy >= 80%** with Sonnet at the end of progressive improvement (baseline: 60%) — **EXCEEDED: 98%**
- **Simple >= 88%** (solving pagination should cover this) — **EXCEEDED: 100%**
- **Complex >= 75%** (baseline: 64%, improvement via multi-turn + reference nav) — **EXCEEDED: 95%**

---

## Exp 3 — Model Matrix

### Hypothesis
Larger models have better accuracy, but local models (Ollama) may be viable for simple queries. GPT-4o should be close to Sonnet.

### Setup
- **Dataset:** 50 questions
- **Models:** Claude Opus 4, Claude Sonnet 4.5, Claude Haiku 4.5, GPT-4o, Ollama (llama3.1:8b)
- **Agent:** Final version from progressive improvement phase

### Results

| Model | Accuracy | Simple | Medium | Complex | Avg Duration | Cost/query |
|--------|----------|--------|--------|---------|-------------|-------------|
| Claude Opus 4 | | | | | | |
| Claude Sonnet 4.5 | | | | | | |
| Claude Haiku 4.5 | | | | | | |
| GPT-4o | | | | | | |
| Ollama llama3.1:8b | | | | | | |

---

## Exp 4 — Ablation Study

### Hypothesis
Each component of the agent contributes measurably to accuracy. Disabling components will show the individual impact of each one.

### Setup
- **Dataset:** 50 questions
- **Model:** Claude Sonnet 4.5
- **Variants:**
  - Full agent (baseline)
  - Without terminology resolver (raw text -> FHIR queries)
  - Without tools (LLM responds only with parametric knowledge)
  - Without Langfuse tracing (verify it doesn't affect performance)
  - Tool call limit = 1 (force single-turn)
  - Temperature = 0.5 (verify non-determinism impact)

### Results

| Variant | Accuracy | Delta vs Full | Notes |
|----------|----------|---------------|-------|
| Full agent | | baseline | |
| Without terminology | | | |
| Without tools | | | |
| Without tracing | | | |
| Max 1 tool call | | | |
| Temperature 0.5 | | | |

---

## Exp 6 — Expanded Dataset: 100 Questions

### Hypothesis
The agent that reached 98% on 50 questions (Exp 5) should maintain >=85% when scaling to 100 questions with 200 patients and 9 resource types. The new resource types (Procedure, AllergyIntolerance, Immunization, DiagnosticReport) and more demanding questions will reveal limitations not visible in the previous dataset.

### Setup
- **Dataset:** 100 questions (15 simple, 35 medium, 50 complex)
- **Data:** 200 Patient + 302 Condition + 375 Observation + 361 MedicationRequest + 437 Encounter + Procedure + AllergyIntolerance + Immunization + DiagnosticReport (3182 total entries, 9 resource types)
- **Agent model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Judge:** Claude Haiku 4.5 (hybrid: programmatic pre-check + LLM)
- **Agent:** Loop v1 with 4 tools (resolve_terminology + search_fhir + get_resource + execute_code), max 8 iterations, timeout 180s
- **No agent changes** from Exp 5 — only the dataset changes

### Results

| Model | Accuracy | Simple (15) | Medium (35) | Complex (50) | Errors | Avg Duration | Avg Iterations |
|--------|----------|-------------|-------------|--------------|--------|-------------|----------------|
| Claude Sonnet 4.5 | **79.0%** | 15/15 (100%) | 24/35 (69%) | 40/50 (80%) | 5 | 56.9s | 3.75 |

### Failure Analysis

**21 total failures:** 16 incorrect + 5 errors

#### Pattern 1: Pagination — First Page Only (12 failures, 57% of failures)

**Questions:** M07, M09, M14, M19, M25, C02, C05, C14, C18, C20, C21, C40

This is the **dominant problem**. The agent uses `_count=200` but several resource types now exceed 200 entries:
- MedicationRequest: 361 entries -> the agent sees 200 (~55%)
- Encounter: 437 entries -> the agent sees 200 (~46%)
- Immunization: 687 entries -> the agent sees 200 (~29%)
- Condition: 302 entries -> the agent sees 200 (~66%)

The agent sometimes detects that there is more data ("200 of 361 total") but still reports partial counts as the final answer. Sub-counts are proportional: M19 reports 91 antihypertensives vs 157 actual (~58%), C20 reports 200 encounters vs 437 (~46%).

In Exp 5 this was not a problem because with 55 patients no resource type exceeded 200 entries.

#### Pattern 2: Timeout (3 failures)

**Questions:** C17, C22, C46

Complex cross-resource queries requiring multiple paginated searches and set intersections. With larger data, 180 seconds is not enough:
- C17: Patients with hospitalizations + prescribed medications
- C22: Patients with any prescribed antihypertensive
- C46: Patients >65 years with COVID-19 AND influenza vaccines

#### Pattern 3: LOINC / Terminology for DiagnosticReport (3 failures)

**Questions:** M26, M27, M35

The agent cannot find complete blood counts (31), metabolic panels (50), or thyroid profiles (39). It searches with LOINC codes that don't match those in the seed, or searches in the wrong resource type. The TerminologyResolver doesn't have the LOINC codes used for DiagnosticReport in seed v3.

#### Pattern 4: Incorrect Metric — Records vs Patients (1 failure)

**Question:** M22

Counts 58 AllergyIntolerance records instead of 43 unique patients with allergies. The agent doesn't deduplicate by patient.

#### Pattern 5: Max iterations exceeded (1 failure)

**Question:** M23

The search for COVID-19 vaccines in 687 Immunization records exhausts all 8 iterations.

#### Pattern 6: Rate limit (1 failure)

**Question:** M24

Error 429 cascade from intensive token usage in M23. Infrastructure error, not logic.

### Results by Question

#### Simple (15/15 = 100%)
S01 OK, S02 OK, S03 OK, S04 OK, S05 OK, S06 OK, S07 OK, S08 OK, S09 OK, S10 OK, S11 OK, S12 OK, S13 OK, S14 OK, S15 OK

#### Medium (24/35 = 69%)
M01 OK, M02 OK, M03 OK, M04 OK, M05 OK, M06 OK, **M07 FAIL** (pagination), M08 OK, **M09 FAIL** (pagination), M10 OK, M11 OK, M12 OK, M13 OK, **M14 FAIL** (pagination), M15 OK, M16 OK, M17 OK, M18 OK, **M19 FAIL** (pagination), M20 OK, M21 OK, **M22 FAIL** (records vs patients), **M23 ERROR** (max iterations), **M24 ERROR** (rate limit), **M25 FAIL** (pagination), **M26 FAIL** (LOINC mismatch), **M27 FAIL** (LOINC mismatch), M28 OK, M29 OK, M30 OK, M31 OK, M32 OK, M33 OK, M34 OK, **M35 FAIL** (LOINC mismatch)

#### Complex (40/50 = 80%)
C01 OK, **C02 FAIL** (pagination), C03 OK, C04 OK, **C05 FAIL** (pagination), C06 OK, C07 OK, C08 OK, C09 OK, C10 OK, C11 OK, C12 OK, C13 OK, **C14 FAIL** (pagination), C15 OK, C16 OK, **C17 ERROR** (timeout), **C18 FAIL** (pagination), C19 OK, **C20 FAIL** (pagination), **C21 FAIL** (pagination), **C22 ERROR** (timeout), C23 OK, C24 OK, C25 OK, C26 OK, C27 OK, C28 OK, C29 OK, C30 OK, C31 OK, C32 OK, C33 OK, C34 OK, C35 OK, C36 OK, C37 OK, C38 OK, C39 OK, **C40 FAIL** (pagination), C41 OK, C42 OK, C43 OK, C44 OK, C45 OK, **C46 ERROR** (timeout), C47 OK, C48 OK, C49 OK, C50 OK

### Conclusion

The 79% is **below the 85% target**. The drop from 98% -> 79% is due almost exclusively to **pagination**: the `_count=200` that was sufficient for 55 patients is not enough for 200 patients. It is a known problem that resurfaces at larger scale.

**Improvement plan (fixes):**
1. **Automatic pagination** — implement multi-page fetch or increase `_count` for aggregation queries (+12 questions, ~+12pp)
2. **LOINC for DiagnosticReport** — add missing codes to the TerminologyResolver (+3 questions, ~+3pp)
3. **Deduplication by patient** — guidance in system prompt to count unique patients (+1 question, ~+1pp)
4. **Max iterations / timeout** — consider bump to 12 iterations or 300s for large queries (+4 questions, ~+4pp)

With these fixes, the optimistic target is **~99%** (79 + 20 recoverable). Realistic: **92-95%**.

---

## Exp 7 — Planner + Cost Baseline

### Hypothesis
The Query Planner (ADR-009) with Action Space Reduction, `count_fhir`, `search_all` (auto-pagination), scratchpad, and prompt v2.0 should recover most of the failures from Exp 6. The 3 problematic questions (M23, C22, C46) are temporarily disabled to avoid wasting tokens on known failures.

### Setup
- **Dataset:** 97 questions (3 disabled: M23, C22, C46) — 15 simple, 34 medium, 48 complex
- **Data:** 3182 entries, 9 resource types (same as Exp 6)
- **Agent model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Judge:** Claude Haiku 4.5 (hybrid)
- **Agent:** Loop with 6 tools (resolve_terminology + search_fhir + get_resource + execute_code + count_fhir + search_all), max 12 iterations, timeout 300s
- **New vs Exp 6:** Planner with classification + ASR, `count_fhir` with `_has`, `search_all` (auto-pagination), scratchpad (`store`), prompt v2.0

### Results

| Model | Accuracy | Simple (15) | Medium (34) | Complex (48) | Errors | Avg Duration | Avg Iterations |
|--------|----------|-------------|-------------|--------------|--------|-------------|----------------|
| Claude Sonnet 4.5 | **88.7%** | 15/15 (100%) | 30/34 (88%) | 41/48 (85%) | 5 | 24.5s | 4.2 |

### Failure Analysis

**11 total failures:** 6 incorrect + 5 errors

#### Incorrect (6)
- **M14** — 9 iterations, 32.0s
- **M16** — 2 iterations, 10.3s
- **M19** — 6 iterations, 29.2s
- **M22** — 2 iterations, 10.9s (records vs patients, same problem as Exp 6)
- **C05** — 11 iterations, 45.9s
- **C15** — 3 iterations, 18.4s

#### Errors (5)
- **C07** — 10.0s (unspecified error)
- **C17** — 20.1s (intermittent error — was CORRECT in previous isolated run)
- **C18** — 10.9s (unspecified error)
- **C26** — 20.1s (unspecified error)
- **C33** — 55.9s (unspecified error)

### Cost Analysis

**Total estimated cost: ~$8.89 USD** (agent $8.66 + planner $0.12 + judge $0.12)

#### Distribution by category

| Category | Questions | Iterations | Input Tokens | Output Tokens | Agent Cost | $/Question |
|-----------|-----------|-------------|--------------|---------------|-------------|------------|
| simple | 15 | 30 | 136,251 | 2,267 | $0.44 | $0.030 |
| medium | 34 | 118 | 598,982 | 18,671 | $2.08 | $0.061 |
| complex | 48 | 256 | 1,730,401 | 63,415 | $6.14 | $0.128 |
| **Total** | **97** | **404** | **2,465,634** | **84,353** | **$8.66** | **$0.089** |

#### Key insight

**85% of the cost is input tokens** ($7.40 of $8.66). The system prompt (~4,300 tokens) is repeated 404 times = $5.26 in static prompt alone. The accumulated history adds $2.14.

#### Top 5 most expensive questions

| ID | Category | Iterations | Input Tokens | Cost | Status |
|----|-----------|-------------|--------------|-------|--------|
| C12 | complex | 10 | 98,563 | $0.333 | CORRECT |
| C38 | complex | 11 | 84,351 | $0.292 | CORRECT |
| C09 | complex | 12 | 71,314 | $0.252 | CORRECT |
| C44 | complex | 9 | 70,971 | $0.244 | CORRECT |
| C19 | complex | 8 | 65,176 | $0.229 | CORRECT |

#### Cost reduction scenarios

| Scenario | Estimated Cost | Savings | Impact |
|-----------|---------------|--------|---------|
| A) System prompt -1500 tokens | $6.84 | $1.82 (21%) | Trim prompt |
| B) Reduce average to 3.0 iters | $6.19 | $2.47 (29%) | More efficient agent |
| C) Simple+Medium to Haiku | $6.81 | $1.85 (21%) | Model routing by complexity |
| D) Prompt caching (90% hit) | $4.40 | $4.26 (49%) | Anthropic API cache |
| E) A + B combined | ~$4.89 | ~$3.77 (44%) | Combined |

### Disabled Questions

3 questions excluded due to known failures that waste tokens without providing new information:

| ID | Problem | Root Cause |
|----|----------|------------|
| M23 | COVID-19 vaccines not found by SNOMED | Data uses CVX, not SNOMED. Missing CVX mapping in terminology |
| C22 | `_has` with `:text` not supported by HAPI | MedicationRequest uses ATC, not SNOMED. Agent spirals with errors |
| C46 | >65 + COVID + influenza, max iterations | Downloads 888 entries, wastes iterations debugging format |

### Conclusion

**88.7% is solid progress** from 79% (Exp 6), achieved mainly by `search_all` (auto-pagination), `count_fhir` (server-side counting), and the planner (reduces unnecessary tools). Average duration dropped from 56.9s to 24.5s.

**Next step:** Cost optimization. The benchmark costs ~$8.66 per run. The main driver is the repeated system prompt (85% of cost is input tokens). Anthropic prompt caching is the biggest lever (49% potential savings).

---

## Exp 8 — Cost Validation: Prompt Caching + System Prompt Diet

### Hypothesis
Anthropic prompt caching (system prompt + tool definitions) combined with system prompt diet (v2.0 -> v2.1, ~45% more compact) should reduce per-run cost by ~35-49%, without affecting accuracy.

### Setup
- **Dataset:** 30 questions (representative sample: 5 simple, 10 medium, 15 complex)
- **Data:** 3182 entries, 9 resource types (same as Exp 7)
- **Agent model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Judge:** Claude Haiku 4.5 (hybrid)
- **Agent:** Same as Exp 7 + prompt caching + system prompt v2.1
- **New vs Exp 7:** `cache_control: {"type": "ephemeral"}` on system prompt and tool definitions. System prompt trimmed ~45%.

### Results

| Model | Accuracy | Simple (5) | Medium (10) | Complex (15) | Errors | Avg Duration | Avg Iterations |
|--------|----------|------------|-------------|--------------|--------|-------------|----------------|
| Claude Sonnet 4.5 | **96.7%** | 5/5 (100%) | 10/10 (100%) | 14/15 (93%) | 1 | 21.4s | 4.5 |

### Cost Analysis

**Actual cost (Anthropic dashboard): $1.81 USD for 30 questions.**

#### Token breakdown (agent only, 30q)

| Metric | Tokens |
|---------|--------|
| Input (non-cached) | 251,450 |
| Output | 26,461 |
| Cache creation | 90,771 |
| Cache read | 391,650 |
| Total LLM calls | 136 |

#### Cost breakdown

| Component | Cost |
|------------|-------|
| Input (non-cached) | $0.75 |
| Cache write (1.25x) | $0.34 |
| Cache read (0.1x) | $0.12 |
| Output | $0.40 |
| **Agent total (30q)** | **$1.61** |
| Planner + Judge | ~$0.20 |
| **Total actual (30q)** | **$1.81** |

#### Comparison with Exp 7

| Metric | Exp 7 | Exp 8 | Delta |
|---------|-------|-------|-------|
| Per question | $0.089 | $0.060 | **-33%** |
| Projected 97q | $8.66 | $5.85 | **-$2.81** |
| Avg duration | 24.5s | 21.4s | -13% |

#### Cache effectiveness

- **391K tokens read from cache** vs 90K written -> cache hit ratio 4.3:1
- Without caching, input would cost $2.20 -> caching saves **38%** of input cost
- The total savings (33%) is less than the theoretical (49%) because: (1) cache write has 1.25x overhead, (2) planner/judge don't benefit from the agent's cache

### Error

- **C44** — max iterations (12). Same problem as Exp 7: triple-cross query (DM2 + glucose >140 + metformin) exhausts iterations.

### Conclusion

**Prompt caching + diet reduce cost ~33%** in a verified way. From $8.66 to ~$5.85 projected for 97 questions. Accuracy is unaffected (96.7% on 30-question sample, consistent with 88.7% on 97). The savings allow ~50% more experiments with the same budget.

---

## Exp 9 — Representative Sample Post-Expansion

### Hypothesis
With 30 strategically selected questions (complete coverage of skills, domains, resource types, and graph hops), the agent should maintain >=90% accuracy. The new CarePlan questions (multi-hop, negation) should pass thanks to the graph and catalog implemented previously.

### Setup
- **Dataset:** 30 selected questions (4 simple, 10 medium, 16 complex)
- **Selection:** Complete coverage — 10/10 skills, 9/9 domains, 10/10 resource types, 6/6 CarePlan questions, hops 0/1/2
- **Data:** 3273 entries, 10 resource types (includes CarePlan)
- **Agent model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Judge:** Claude Haiku 4.5 (hybrid)
- **Agent:** 6 tools, max 15 iterations, timeout 300s, prompt caching + diet v2.1
- **New vs Exp 8:** CarePlan (10th resource type), 16 new questions from expanded taxonomy, sample with more complex (16/30 = 53% vs 15/30 = 50%)

### Results

| Model | Accuracy | Simple (4) | Medium (10) | Complex (16) | Errors |
|--------|----------|-----------|-----------|-----------|--------|
| Claude Sonnet 4.5 | **90.0%** | 4/4 (100%) | 9/10 (90%) | 14/16 (88%) | 0 |

### Results by Question

#### Simple (4/4 = 100%)
| ID | Domain | Hops | Iters | Status |
|----|---------|------|-------|--------|
| S01 | demographics | 0 | 2 | OK |
| S09 | surgery | 0 | 2 | OK |
| S10 | vaccination | 0 | 2 | OK |
| S16 | care_coordination | 0 | 2 | OK (**new CarePlan**) |

#### Medium (9/10 = 90%)
| ID | Domain | Hops | Skills | Iters | Status | Notes |
|----|---------|------|--------|-------|--------|-------|
| M01 | chronic_disease | 1 | terminology | 3 | OK | |
| M09 | chronic_disease | 0 | aggregation, code_exec | 3 | OK | |
| M11 | laboratory | 0 | terminology | 3 | OK | |
| M14 | medication | 0 | terminology | 8 | **FAIL** | ATC vs SNOMED — see analysis |
| M17 | care_coordination | 1 | filtering | 8 | OK | Expensive but correct |
| M22 | safety | 1 | counting | 3 | OK | |
| M25 | vaccination | 0 | aggregation | 3 | OK | |
| M36 | care_coordination | 0 | filtering | 2 | OK (**new CarePlan**) |
| M37 | care_coordination | 1 | cross_resource | 3 | OK (**new CarePlan**) |
| M42 | laboratory | 1 | reference_nav | 6 | OK (**new**) |

#### Complex (14/16 = 88%)
| ID | Domain | Hops | Skills | Iters | Status | Notes |
|----|---------|------|--------|-------|--------|-------|
| C03 | epidemiology | 1 | aggregation, code_exec | 4 | OK | |
| C08 | medication | 2 | cross_resource | 10 | OK | |
| C10 | laboratory | 2 | cross_resource, filter | 9 | OK | |
| C13 | laboratory | 2 | calculation, code_exec | 6 | OK | |
| C17 | care_coordination | 2 | cross_resource | 4 | **FAIL** | Incorrect hospitalization filter |
| C20 | epidemiology | 1 | aggregation, code_exec | 3 | OK | |
| C24 | care_coordination | 0 | temporal | 7 | OK | |
| C27 | chronic_disease | 1 | negation | 5 | OK | |
| C28 | medication | 2 | negation, cross_res | 10 | OK | |
| C38 | safety | 2 | cross_resource | 8 | OK | |
| C39 | vaccination | 1 | filtering | 5 | OK | |
| C43 | chronic_disease | 1 | calculation, code_exec | 5 | OK | |
| C51 | care_coordination | 2 | cross_resource | 3 | OK (**new CarePlan**) |
| C53 | care_coordination | 2 | calc, code_exec | 11 | OK (**new CarePlan**) |
| C55 | surgery | 2 | cross_resource, code | 9 | **FAIL** | Incomplete chronic condition definition |
| C62 | care_coordination | 2 | negation, code_exec | 9 | OK (**new CarePlan**) |

### Failure Analysis

**3 incorrect, 0 errors.** Each failure has a distinct root cause:

#### Failure 1: M14 — Metformin Not Found (ATC vs SNOMED)

**Question:** "How many patients have a metformin prescription?"
**Expected:** 32 patients. **Agent:** 0 patients.

**Root cause:** MedicationRequest uses ATC codes (A10BA02), not SNOMED. The TerminologyResolver doesn't have metformin with an ATC code. The agent tried with SNOMED (372567009), free text, and variants — none worked with `_has`. Wasted 8 iterations and 7 tool calls searching without finding.

**This failure is recurrent:** M14 also failed in Exp 7.

**Candidate fix:** Add the ATC coding system to the TerminologyResolver, or at least a mapping `metformin -> ATC A10BA02` in the locale pack.

#### Failure 2: C17 — Patients with Hospitalizations + Medications (incorrect filter)

**Question:** "How many patients with hospitalizations have prescribed medications?"
**Expected:** 53 patients. **Agent:** 151 patients.

**Root cause:** The agent did not filter Encounters by class `IMP` (hospitalization). It counted ALL patients with any Encounter (151) that also have MedicationRequest, instead of only those with hospitalization-type Encounters. The planner classified as `count_with_resource` but didn't specify the `class=IMP` filter.

**Candidate fix:** Add to the planner knowledge that "hospitalization" = Encounter with `class=IMP`. The QueryPattern catalog could include a specific pattern for encounter class filters.

#### Failure 3: C55 — Incomplete "chronic condition" definition (hardcoded)

**Question:** "How many patients with procedures have at least one chronic condition?"
**Expected:** 47 patients. **Agent:** 34 patients.

**Root cause:** The agent hardcoded a list of 6 chronic conditions (DM2, HTA, COPD, asthma, HF, CKD) in `execute_code`. It missed the other chronic conditions in the system (hypothyroidism, rheumatoid arthritis, etc.). The intersection undercounted because the "chronic" definition was partial.

**Candidate fix:** No simple fix — requires the agent to query ALL conditions and programmatically determine which are chronic (by clinical-status or by the LLM's medical knowledge). Alternative: improve the system prompt with guidance that "chronic condition" includes everything that is not acute.

### Positive Signals

- **CarePlan: 6/6 correct** — all new CarePlan questions passed, including multi-hop (C51, C53) and negation (C62). The graph and catalog work.
- **0 errors** — no crashes, timeouts, or rate limits. Infrastructure is stable.
- **Negation works** — C27, C28, C62 all correct. The agent handles "patients who do NOT have X."
- **Reference navigation works** — M42 (DiagnosticReport -> Observation) correct.
- **Temporal works** — C24 correct.

### Conclusion

**90% confirms that the agent is robust** in most scenarios. The 3 failures are specific and actionable:
1. **M14/C17** are terminology/catalog problems — fixes in the TerminologyResolver and planner would resolve them.
2. **C55** is a clinical reasoning problem — the agent doesn't know which conditions are "chronic" without an explicit list.

The new features (CarePlan, negation, reference_navigation, temporal) work correctly. The FHIR graph and planner are fulfilling their role.

---

## Master Results Table

Complete history of all benchmark executions.

| Exp | Model | Dataset | Accuracy | Simple | Medium | Complex | Notes |
|-----|--------|---------|----------|--------|--------|---------|-------|
| 0 | Sonnet 4.5 | 25q (v1) | 88.0% | 88% | 100% | 71% | Inflated baseline |
| 1 | Sonnet 4.5 | 50q (v2) | 60.0% | 50% | 60% | 64% | Honest baseline |
| 2 | Sonnet 4.5 | 50q (v2) | 82.0% | 100% | 80% | 77% | Pagination fix (`_count=200`, `_summary=count`) |
| 3 | Sonnet 4.5 | 50q (v2) | 86.0% | 100% | 95% | 73% | Terminology fix, `get_resource` tool, max_iterations=8, prompt v1.2 |
| 4 | Sonnet 4.5 | 50q (v2) | 94.0% | 100% | 95% | 91% | Code interpreter (`execute_code`), prompt v1.3 |
| 5 | Sonnet 4.5 | 50q (v2) | 98.0% | 100% | 100% | 95% | Judge regex fix (bare ranges, %), timeout 180s |
| 6 | Sonnet 4.5 | 100q (v3) | 79.0% | 100% | 69% | 80% | Expanded dataset: 200 patients, 9 resource types, 100 questions |
| 7 | Sonnet 4.5 | 97q (v3) | 88.7% | 100% | 88% | 85% | Planner + ASR + count_fhir + search_all + scratchpad. 3 questions disabled (M23, C22, C46). Cost: ~$8.66 agent |
| 8 | Sonnet 4.5 | 30q (v3 sample) | 96.7% | 100% | 100% | 93% | Prompt caching + system prompt diet v2.1. Actual cost: $1.81 (30q), projected $5.85 (97q). **-33% vs Exp 7** |
| 9 | Sonnet 4.5 | 30q (v3 representative) | 90.0% | 100% | 90% | 88% | Representative sample post-expansion: 10/10 skills, 9/9 domains, 10/10 resources, 6/6 CarePlan OK. 3 failures: M14 (ATC), C17 (IMP filter), C55 (chronic hardcoded) |

---

## Exp 11 — Multi-LLM: Qwen 3.5 9B

### Hypothesis
A 9B-parameter open-source model can execute the same agent pipeline
(planner + tools + judge) but with significantly lower accuracy than a frontier model.
This experiment establishes the floor of the multi-LLM comparison table.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C). Selected from 119 for maximum diversity, 19 redundant disabled. See `BENCHMARK_TAXONOMY.md`.
- **Data:** Seed v3 (200 patients, 10 resource types, 3273 entries)
- **Agent model:** Qwen 3.5 9B (`Qwen/Qwen3.5-9B`) via Together AI
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Timeout:** 300s
- **Infrastructure:** Together AI serverless API (OpenAI-compatible)

### Results

Initial run + retry of 503 errors (with `--delay 3` between questions):

| Model | Accuracy | Simple | Medium | Complex | Errors | Avg latency | Tokens/q |
|--------|----------|--------|--------|---------|--------|-------------|----------|
| Qwen 3.5 9B | **29.0%** | 9/16 (56%) | 18/41 (44%) | 2/43 (5%) | 10 | 30.5s | 7.0K |
| Qwen 3.5 9B (excl errors) | **32.2%** | — | — | — | — | — | — |

**Latency distribution (initial run, 100q):**

| Metric | avg | p50 | p75 | p90 | p95 |
|--------|-----|-----|-----|-----|-----|
| Duration (s) | 30.5 | 17.1 | 31.0 | 72.4 | 128.5 |
| Iterations | 1.8 | 2.0 | 3.0 | 3.0 | 4.0 |
| Tool calls | 1.7 | 1.0 | 2.0 | 4.0 | 5.0 |

**Token usage:** ~924K total (~871K in + ~53K out, summing both runs). ~$0.12 agent cost.

**Results:**
- Initial run: `benchmarks/results/eval_20260321_181516.json`
- Retry (27q with errors): `benchmarks/results/eval_20260321_183748.json`
- Combined progress: `benchmarks/results/progress_qwen_retry.jsonl`

### Analysis

**Together AI 503 errors:** The initial run had 27/100 HTTP 503 "Service Unavailable" errors — Together AI could not serve the request. The OpenAI SDK retries automatically (2 retries), but in 27 cases it exhausted retries. The 27 questions were retried with `--delay 3` (3-second pause between questions), recovering 17 of 27. The 10 persistent errors are all Complex (7) and Medium (3) — questions that generate more tokens and more tool calls, saturating the API.

**Failure patterns:**
- **`answer_length=0` (main):** Qwen frequently makes the correct tool call, gets the result, but in the final iteration returns an empty response (doesn't generate narrative text). This represents the majority of INCORRECT in Simple/Medium. The model seems not to understand that it must produce a natural language response after receiving the data.
- **Complex (5%):** The model lacks multi-hop reasoning capability. Almost all complex questions fail because Qwen cannot plan the correct sequence of tool calls (resolve_terminology -> search -> filter -> count).
- **Terminology:** When it does invoke `resolve_terminology`, it works (the resolver is deterministic). But it often doesn't invoke the tool or doesn't use the returned code in the next query.

**Conclusion:** 9B is insufficient for the FHIR agent, but the pipeline works end-to-end with open-source models via Together AI. The result is useful as the floor of the comparison table. Together AI infrastructure introduces significant noise (503 errors) that must be controlled with pauses between requests.

---

## Exp 12 — Multi-LLM: Llama 3.3 70B

### Hypothesis
A 70B-parameter open-source model should significantly outperform the 9B model
and approach commercial models on simple/medium questions, but fall on complex.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C)
- **Data:** Seed v3 (200 patients, 10 resource types, 3273 entries)
- **Agent model:** Llama 3.3 70B Instruct Turbo (`meta-llama/Llama-3.3-70B-Instruct-Turbo`) via Together AI
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Timeout:** 300s
- **Delay:** 1s between questions (initial run), 3s (retry)

### Results

Initial run + retry of 13 503 errors:

| Model | Accuracy | Simple | Medium | Complex | Errors | Avg latency | Tokens/q |
|--------|----------|--------|--------|---------|--------|-------------|----------|
| Llama 3.3 70B | **46.9%** | 15/16 (94%) | 23/41 (56%) | 8/41 (20%) | 7 | 6.6s | 6.3K |
| Llama 3.3 70B (excl errors) | **50.5%** | — | — | — | — | — | — |

**Latency distribution (initial run, 100q):**

| Metric | avg | p50 | p75 | p90 | p95 |
|--------|-----|-----|-----|-----|-----|
| Duration (s) | 6.6 | 5.3 | 9.0 | 11.5 | 13.1 |
| Iterations | 2.1 | 2.0 | 2.0 | 3.0 | 5.0 |
| Tool calls | 1.2 | 1.0 | 1.0 | 2.0 | 4.0 |

**Token usage:** ~853K total (run + retry). ~$0.75 agent cost.

**Results:**
- Initial run: `benchmarks/results/eval_20260321_190310.json`
- Retry (13q): `benchmarks/results/llama3.3-70b_retry.log`
- Combined progress: `benchmarks/results/progress_llama_retry.jsonl`

### Analysis

**Simple (94%):** Nearly perfect — only 1 failure. The model understands basic FHIR and tool calling.

**Medium (56%):** Reasonable. Resolves terminology correctly when it invokes the tool, but sometimes doesn't invoke it or doesn't connect the code with the next FHIR query.

**Complex (20%):** Very low. The model cannot reliably plan multi-hop sequences.

**Errors (7 final, all `max_iterations_exceeded`):**
- Initial run: 13 503 errors from Together AI. Retry with `--delay 3` recovered 6.
- The remaining 7 are reasoning errors, not infrastructure:
  - Incorrect `_has` syntax: Llama doesn't understand the `_has:Resource:searchParam:code` structure and generates invalid variants like `_has:Condition:subject:not-exists`.
  - Passing JSON objects as arguments: in late iterations, the model degenerates and passes `{'type': 'string', 'value': 'Patient'}` instead of `'Patient'`.
  - Repetitive loop: repeats the same invalid query 5-8 times without correcting.

**Comparison with Qwen 3.5 9B:**

| Dimension | Qwen 3.5 9B | Llama 3.3 70B | Delta |
|-----------|-------------|---------------|-------|
| Accuracy | 29.0% | 46.9% | +17.9pp |
| Simple | 56% | 94% | +38pp |
| Medium | 44% | 56% | +12pp |
| Complex | 5% | 20% | +15pp |
| Latency | 30.5s | 6.6s | -78% |

**Conclusion:** 70B is significantly better than 9B across all dimensions. Simple is nearly perfect. But Complex remains the bottleneck — multi-hop reasoning and advanced FHIR syntax (`_has`, negation) are too difficult for open-source models of this size. The 5x lower latency compared to Qwen is notable (more efficient model on Together + fewer retries).

---

## Exp 13 — Multi-LLM: GPT-4o

### Hypothesis
GPT-4o with schema flattening, retry, and `suggested_query` should significantly outperform
open-source models and approach Claude Sonnet.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C)
- **Data:** Seed v3 (200 patients, 10 resource types)
- **Agent model:** GPT-4o via OpenAI API
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Delay:** 2s between questions
- **Fixes applied:**
  - Schema flattening (`_flatten_params_for_openai`) — active for native OpenAI
  - Retry with exponential backoff (429, 503, 529)
  - `_merge_params()` tool argument normalization
  - `suggested_query` in planner
  - FHIR port 8890, preflight check

### Results

| Model | Accuracy | Simple | Medium | Complex | Errors |
|--------|----------|--------|--------|---------|--------|
| GPT-4o | **63.0%** | 16/16 (100%) | 30/41 (73%) | 17/43 (40%) | 3 |

**Progress:** `benchmarks/results/progress_20260322_224328.jsonl`

### Analysis

**Simple (100%):** Schema flattening completely solved the problem. GPT-4o now
generates filters as top-level keys (`{"resource_type": "Patient", "gender": "male"}`).
Without flattening, Simple was 53%.

**Medium (73%):** Failures in terminology resolution (M04 asthma, M19 antihypertensives,
M24 influenza vaccine, M26 complete blood count). GPT-4o doesn't always invoke `resolve_terminology`
or doesn't connect the resolved code with the FHIR query.

**Complex (40%):** Reasonable for a model without FHIR fine-tuning. Failures in comorbidity
queries (C10, C05), geographic aggregation (C03), and multi-hop queries.

**Errors (3):**
- 2x `max_iterations_exceeded` (C44, M37)
- 1x parse error: GPT-4o generated truncated JSON in tool arguments (C64)

### Comparison

| Model | Accuracy | Simple | Medium | Complex | Errors |
|--------|----------|--------|--------|---------|--------|
| Claude Sonnet 4.5 | 93.3%* | 100% | 100% | 88% | 0 |
| GPT-4o | 63.0% | 100% | 73% | 40% | 3 |
| Llama 3.3 70B | 48.0% | 94% | 63% | 16% | 9 |
| Qwen 3.5 9B | 25.0% | 50% | 29% | 12% | 1 |

*Sonnet based on Exp 10 (30q sample). Pending re-run with 100q.

**Conclusion:** GPT-4o is clearly the second-best model. The gap with Claude Sonnet
(-30pp) concentrates in Medium (-27pp) and Complex (-48pp), where Claude leverages
tool calling and advanced FHIR syntax better. Simple is identical thanks to
schema flattening.

---

## Exp 14 — Multi-LLM: Qwen 3.5 9B Re-run

### Hypothesis
The multi-LLM compatibility fixes (retry with backoff, `_merge_params`,
`suggested_query` in planner) should improve Qwen by eliminating 503 errors
and normalizing tool arguments.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C)
- **Data:** Seed v3 (200 patients, 10 resource types)
- **Agent model:** Qwen 3.5 9B via Together AI
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Delay:** 2s between questions
- **Changes vs Exp 11:**
  - Retry with exponential backoff (429, 503, 529) — 4 retries, 1->2->4->8s
  - `_merge_params()` normalizes params to top-level or in `additionalProperties`
  - `suggested_query` in planner (concrete query injected into system prompt)
  - Schema flattening **disabled** for Together AI (`base_url != None`)
  - FHIR port: 8890 (dedicated for SaludAI)
  - Preflight check: verifies 200 patients before running

### Results

| Model | Accuracy | Simple | Medium | Complex | Errors |
|--------|----------|--------|--------|---------|--------|
| Qwen 3.5 9B (Exp 11) | 29.0% | 9/16 (56%) | 18/41 (44%) | 2/43 (5%) | 10 |
| Qwen 3.5 9B (Exp 14) | **25.0%** | 8/16 (50%) | 12/41 (29%) | 5/43 (12%) | **1** |

**Progress:** `benchmarks/results/progress_20260322_213514.jsonl`

### Analysis

**Retry eliminated almost all errors:** 10 -> 1. The only remaining error is a
`Connection error` from Together AI (not a retryable 503/429).

**Accuracy dropped slightly (29% -> 25%).** The `suggested_query` from the planner may
be confusing Qwen on some Medium questions — the model tries to follow the suggestion
but doesn't always execute it correctly. In Complex it rose from 5% to 12%, which
suggests the suggestion helps on harder questions where Qwen wouldn't know
where to start.

**Inherent variance:** Qwen 9B has high variability between runs. The 4pp difference
is not significant — the model simply isn't capable enough for robust FHIR
tool calling.

**Schema flattening discarded for Together AI.** In an intermediate run with flattening
active, Qwen dropped to 13% (82/86 empty responses). The model interprets
`additionalProperties` as a literal field and gets confused. Fix: flattening only for
native OpenAI (`base_url is None`).

### Conclusion

For 9B models, infrastructure fixes (retry, normalization) help with
stability but not with capability. The ceiling for Qwen 9B is ~25-30% on this benchmark.

---

## Exp 15 — Multi-LLM: Llama 3.3 70B Re-run

### Hypothesis
The same compatibility fixes (retry, `_merge_params`, `suggested_query`)
should improve Llama by eliminating 503 errors from Together AI.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C)
- **Data:** Seed v3 (200 patients, 10 resource types)
- **Agent model:** Llama 3.3 70B Instruct Turbo via Together AI
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Delay:** 2s between questions
- **Changes vs Exp 12:** same as Exp 14 (retry, `_merge_params`, `suggested_query`,
  schema flattening disabled for Together, port 8890, preflight check)

### Results

| Model | Accuracy | Simple | Medium | Complex | Errors |
|--------|----------|--------|--------|---------|--------|
| Llama 3.3 70B (Exp 12) | 46.9% | 15/16 (94%) | 23/41 (56%) | 8/41 (20%) | 7 |
| Llama 3.3 70B (Exp 15) | **48.0%** | 15/16 (94%) | 26/41 (**63%**) | 7/43 (16%) | 9 |

**Progress:** `benchmarks/results/progress_20260322_222343.jsonl`

### Analysis

**Simple (94%):** Identical. Llama handles demographic filters correctly.

**Medium (63% vs 56%):** +7pp improvement. The `suggested_query` from the planner helps Llama
start with the correct query instead of guessing.

**Complex (16% vs 20%):** Slight drop. 8 of the 9 errors are Complex with `max_iterations`
— Llama enters loops with invalid `_has` syntax or degenerates passing JSON objects
as strings in late iterations (same pattern as Exp 12).

**Errors (9, all `max_iterations_exceeded`):** Zero infrastructure errors — the
retry completely eliminated Together's 503s. All 9 errors are reasoning errors:
the model cannot break out of loops of invalid queries.

### Conclusion

Llama 3.3 70B benefits from `suggested_query` in Medium (+7pp). Retry eliminated
infrastructure errors. The Complex ceiling (~20%) is limited by the model's capacity
for multi-hop reasoning and advanced FHIR syntax (`_has`, negation).

---

## Exp 16 — Claude Haiku 4.5 100q

### Hypothesis

Claude Haiku 4.5, as a model from the same family as Sonnet but smaller and faster,
should achieve accuracy significantly higher than GPT-4o and open-source models,
approaching Sonnet but with lower cost and latency.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C)
- **Data:** Seed v3 (200 patients, 10 resource types)
- **Agent model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Delay:** 0s (no throttling needed — Anthropic API stable)

### Results

| Model | Accuracy | Simple | Medium | Complex | Errors | Avg Duration | Avg Iters |
|--------|----------|--------|--------|---------|--------|-------------|-----------|
| Claude Haiku 4.5 | **77.0%** | 16/16 (100%) | 33/41 (80%) | 28/43 (65%) | 7 | 9.3s | 3.2 |

**Token usage:** 1.25M total (1.18M in + 65K out). ~12.5K tokens/query.
**Accuracy excluding errors:** 82.8% (77/93).
**Progress:** `benchmarks/results/progress_20260322_233846.jsonl`
**Results:** `benchmarks/results/eval_20260322_235413.json`

### Analysis by Category

**Simple (100%):** Perfect, like all Anthropic models.

**Medium (80%, 1 error):**
8 incorrect + 1 error. Main problems:
- **M22** (recorded allergies): Responds 0 — doesn't find AllergyIntolerance. Possible FHIR search failure.
- **M24** (influenza vaccine): Responds 0 — doesn't resolve Immunization code correctly.
- **M31** (procedures 2024): 58 vs 21 expected — doesn't filter by date correctly.
- **M35** (thyroid profiles): 100 vs 39 — counts individual TSH Observations instead of profiles (DiagnosticReport).
- **M37** (care plan): 62 vs 91 — filters only `active` instead of all statuses.
- **M40** (food allergies): 7 vs 21 — incomplete `food` category filter.
- **M42** (lipid panels with cholesterol): error due to max_iterations.
- **M19** (antihypertensives): 121 vs 157 — doesn't include all antihypertensive ATC codes.

**Complex (65%, 6 errors):**
9 incorrect + 6 errors (`max_iterations`).

Errors (max_iterations — Haiku cannot complete in 8 iterations):
- **C04** (DM2 + HTA): comorbidity multi-resource, requires intersection.
- **C17** (hospitalizations + medications): requires crossing Encounter + MedicationRequest.
- **C20** (encounter distribution by province): requires complex geographic aggregation.
- **C30** (DM2 without HbA1c): multi-resource negation.
- **C54** (DM2 + metabolic panel): cross Condition + DiagnosticReport.
- **C64** (3+ chronic without care plan): multi-hop with counting and negation.

Incorrect — main patterns:
- **Incorrect temporal filters:** C24 (encounters 2024: 437 vs 207), C26 (meds 2024: 361 vs 181) — returns totals without filtering by date.
- **Failed negation:** C27 (patients without conditions: 200 vs 30) — doesn't do the subtraction correctly.
- **Incorrect intersection:** C05 (under 18 with conditions: 0 vs 33), C12 (DM2+HTA+med: 49 vs 9).
- **Incomplete search:** C38 (aspirin allergy+prescription), C58 (emergency 2024), C61 (glucose>140+metformin).

### Updated Multi-LLM Comparison

| Model | Accuracy | Simple | Medium | Complex | Errors | Avg Duration | Tokens/query |
|--------|----------|--------|--------|---------|--------|-------------|-------------|
| Claude Sonnet 4.5* | 93.3% | 100% | 100% | 88% | 0 | ~20s | ~30K |
| **Claude Haiku 4.5** | **77.0%** | **100%** | **80%** | **65%** | **7** | **9.3s** | **12.5K** |
| GPT-4o | 63.0% | 100% | 73% | 40% | 3 | ~15s | ~20K |
| Llama 3.3 70B | 48.0% | 94% | 63% | 16% | 9 | ~12s | ~15K |
| Qwen 3.5 9B | 25.0% | 50% | 29% | 12% | 1 | ~8s | ~10K |

*Sonnet based on Exp 10 (30q). Pending re-run with 100q dataset v4.

### Conclusion

Haiku ranks between Sonnet and GPT-4o, as expected. 77% is solid considering it
is ~10x cheaper than Sonnet. Strengths:

1. **Perfect Simple** — like Sonnet, the Anthropic family dominates basic filters.
2. **Competitive Medium (80%)** — surpasses GPT-4o (73%) by a good margin.
3. **Complex is the gap** — 65% vs 88% from Sonnet. The 7 errors are all queries that
   require 8+ iterations of multi-hop reasoning that Haiku can't achieve within the budget.

Haiku's bottleneck is not tool calling (that works fine) but multi-step reasoning:
set intersections, negation, correct temporal filters. Increasing
`max_iterations` to 12 could recover the 7 errors, but the 9 incorrect answers require
better reasoning, not more iterations.

---

## Exp 17 — Claude Sonnet 4.5 100q

### Hypothesis

Claude Sonnet 4.5, the agent's primary model, should maintain the ~93% accuracy
observed in Exp 10 (30q) when scaling to 100 questions with `max_iterations=8`.

### Setup
- **Dataset:** v4 — 100 questions (16S / 41M / 43C)
- **Data:** Seed v3 (200 patients, 10 resource types)
- **Agent model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Judge model:** Claude Haiku 4.5 (fixed, Anthropic)
- **Max iterations:** 8
- **Delay:** 0s
- **Changes vs Exp 10:** dataset v4 (100q vs 30q), same infra

### Results

| Model | Accuracy | Simple | Medium | Complex | Errors | Avg Duration | Avg Iters |
|--------|----------|--------|--------|---------|--------|-------------|-----------|
| Claude Sonnet 4.5 | **84.0%** | 15/16 (94%) | 38/41 (93%) | 31/43 (72%) | 8 | 17.7s | 3.4 |

**Token usage:** 446K total (383K in + 63K out). ~4.5K tokens/query.
**Accuracy excluding errors:** 91.3% (84/92).
**Progress:** `benchmarks/results/progress_20260323_000906.jsonl`
**Results:** `benchmarks/results/eval_20260323_003838.json`

### Analysis by Category

**Simple (94%, 1 incorrect):**
- **S14** (under 18): 33 vs 39 expected. Age calculation with inconsistent
  cutoff date. First time Sonnet fails a Simple.

**Medium (93%, 1 error):**
3 incorrect + 1 error.
- **M19** (antihypertensives): error max_iterations — requires searching multiple ATC codes.
- **M35** (thyroid profiles): 100 vs 39 — counts TSH Observations instead of
  thyroid profile DiagnosticReports. Same error as Haiku.
- **M40** (food allergies): 7 vs 21 — incomplete `food` category filter.
  Same error as Haiku.

**Complex (72%, 7 errors):**
5 incorrect + 7 errors (all `max_iterations`).

Errors (max_iterations — queries requiring >8 iterations):
- **C10, C44, C61**: glucose + DM2 + metformin — variants of the same multi-hop pattern.
- **C12** (DM2 + HTA + medication): triple intersection.
- **C19** (BA + HTA + meds + BP): quadruple filter.
- **C30** (DM2 without HbA1c): multi-resource negation.
- **C56** (CarePlan DM2 + metformin): triple cross.

Incorrect:
- **C05** (under 18 with conditions): 0 vs 33 — same age confusion as S14.
- **C55** (procedure + chronic): 160 vs 47 — "chronic" definition too broad.
- **C58** (emergency 2024): 75 vs 36 — doesn't filter by class `EMER` correctly.
- **C62** (DM2 without CarePlan): 36 vs 27 — counts only `active` vs all statuses.
- **C64** (3+ chronic without CarePlan): 10 vs 17 — same "chronic" criteria.

### Comparison: Sonnet 30q vs 100q

| Metric | Exp 10 (30q) | Exp 17 (100q) | Delta |
|--------|-------------|---------------|-------|
| Accuracy | 93.3% | 84.0% | -9.3pp |
| Simple | 100% | 94% | -6pp |
| Medium | 100% | 93% | -7pp |
| Complex | 88% | 72% | -16pp |
| Errors | 0 | 8 | +8 |

The drop is explained by:
1. **max_iterations=8 insufficient** for 8 Complex multi-hop questions (in Exp 7 with
   max_iter=12 it achieved 88.7%). The 30q sample avoided the most expensive questions.
2. **New questions in v4** that were not in the 30q sample (M40, C55, C58, C62, C64).
3. **S14/C05** — unexpected regression in age calculation.

### Final Multi-LLM Table (100q, max_iter=8)

| Model | Accuracy | Acc (excl err) | Simple | Medium | Complex | Errors | Avg Duration | Tokens/query |
|--------|----------|---------------|--------|--------|---------|--------|-------------|-------------|
| **Claude Sonnet 4.5** | **84.0%** | **91.3%** | 94% | 93% | 72% | 8 | 17.7s | 4.5K |
| Claude Haiku 4.5 | 77.0% | 82.8% | 100% | 80% | 65% | 7 | 9.3s | 12.5K |
| GPT-4o | 63.0% | — | 100% | 73% | 40% | 3 | ~15s | ~20K |
| Llama 3.3 70B | 48.0% | — | 94% | 63% | 16% | 9 | ~12s | ~15K |
| Qwen 3.5 9B | 25.0% | — | 50% | 29% | 12% | 1 | ~8s | ~10K |

**Note:** Sonnet uses prompt caching (3.8K input/q vs 12.5K for Haiku), which reduces
tokens but not reasoning.

### Conclusion

Sonnet 4.5 confirms its leadership with 84% (91.3% excluding errors), but the
`max_iterations=8` cap costs it 8 Complex questions that require more steps. With
max_iter=12 (as in Exp 7) it would likely recover those errors and reach ~90%.

The final ranking is clear: Sonnet > Haiku > GPT-4o > Llama > Qwen. The Anthropic family
dominates in FHIR tool calling, with Sonnet excelling in Complex multi-hop and Haiku offering
the best cost/performance balance.

---

## Appendix

### A. Dataset Structure

| Dataset | Category | Count | Subcategories |
|---------|-----------|----------|---------------|
| v2 (50q) | simple | 8 | count, demographics, existence |
| v2 (50q) | medium | 20 | terminology, filter_combined, status_filter, aggregation, observation_query, medication_query, encounter_query |
| v2 (50q) | complex | 22 | multi_filter, multi_resource, comorbidity, age_condition, multi_terminology, aggregation_geographic, cross_resource, calculation, reference_traversal, advanced_aggregation |
| v3 (100q) | simple | 15 | count, demographics, existence |
| v3 (100q) | medium | 35 | terminology, filter_combined, status_filter, aggregation, observation_query, medication_query, encounter_query, allergy_query, immunization_query, diagnostic_query |
| v3 (100q) | complex | 50 | multi_filter, multi_resource, comorbidity, age_condition, multi_terminology, aggregation_geographic, cross_resource, calculation, reference_traversal, advanced_aggregation, temporal, negative, correlation |
| v4 (100q) | simple | 16 | count, demographics, existence |
| v4 (100q) | medium | 41 | terminology, filter_combined, status_filter, aggregation, observation_query, medication_query, encounter_query, allergy_query, immunization_query, diagnostic_query, careplan_query |
| v4 (100q) | complex | 43 | Selected from 62->43 for maximum diversity. 19 redundant disabled. 10 skills, 9 domains, 10 resource types. See `BENCHMARK_TAXONOMY.md`. |

### B. Resource Types in Seed v3

| Resource | v2 Count | v3 Count | Code Source | Correlations |
|----------|-------------|-------------|-------------------|---------------|
| Patient | 55 | 200 | DNI (RENAPER) | Province weighted by population |
| Condition | 80 | 302 | SNOMED CT AR | 16 conditions, 5 guaranteed (DM2+BA+>60) |
| Observation | 163 | 375 | LOINC | 6+ types, values correlated with conditions |
| MedicationRequest | 116 | 361 | ATC (WHO) | 10 medications, correlated with conditions |
| Encounter | 122 | 437 | HL7 v3 ActCode | 4 types (AMB 55%, EMER 20%, IMP 15%, HH 10%) |
| Procedure | — | ~200 | SNOMED CT | Procedures associated with conditions |
| AllergyIntolerance | — | ~58 | SNOMED CT | Drug and substance allergies |
| Immunization | — | ~687 | CVX / ATC | Vaccines (COVID-19, influenza, IPV, etc.) |
| DiagnosticReport | — | ~120 | LOINC | Complete blood counts, metabolic panels, thyroid profiles |

### C. Clinical Correlations in Seed

| Condition | Affected Observations | Associated Medications |
|-----------|----------------------|----------------------|
| DM2 (44054006) | Glucose ↑, HbA1c ↑ | Metformin, NPH Insulin |
| HTA (59621000) | Systolic BP ↑, Diastolic BP ↑ | Enalapril, Losartan, Atenolol, Amlodipine |
| Anemia (267036007) | Hemoglobin ↓ | — |
| Asthma (195967001) | — | Salbutamol |
| DM1 (73211009) | — | NPH Insulin |
