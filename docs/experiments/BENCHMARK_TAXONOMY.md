# FHIR-AgentBench — Taxonomy & Question Groups

> Reference document for understanding benchmark results. Use this to identify
> which types of questions fail and prioritize tuning efforts.

**Dataset version:** v3 (100 questions, March 2026)
**Selection criteria:** Maximum diversity with minimum redundancy.

---

## Overview

| Category | Count | Description |
|----------|-------|-------------|
| Simple | 16 | Single resource, 0 hops, basic counting/filtering |
| Medium | 41 | 1-2 resources, terminology resolution, aggregation |
| Complex | 43 | Multi-hop, code execution, negation, cross-resource |
| **Total** | **100** | |

| Dimension | Coverage |
|-----------|----------|
| Skills | 10/10 |
| Domains | 9/9 |
| Resource types | 10/10 |
| Graph hops | 0, 1, 2 |

---

## Coverage Distribution

### By Skill

| Skill | Count | Description |
|-------|-------|-------------|
| counting | 66 | Count resources matching criteria |
| terminology | 51 | Resolve medical terms to SNOMED/LOINC/ATC codes |
| cross_resource | 27 | Follow references between resource types |
| filtering | 25 | Filter by demographic/clinical attributes |
| code_execution | 18 | Python sandbox for aggregation/calculation |
| aggregation | 10 | Group-by, distributions, top-N |
| temporal | 6 | Date range filters (year, period) |
| negation | 6 | "Without X", "not prescribed" patterns |
| calculation | 5 | Averages, ratios, computed values |
| reference_navigation | 5 | Explicit reference traversal (DiagReport→Obs) |

### By Domain

| Domain | Count | Critical? | Notes |
|--------|-------|-----------|-------|
| chronic_disease | 28 | | Core use case — diabetes, hypertension, etc. |
| care_coordination | 16 | | CarePlan, encounters, multi-resource |
| laboratory | 14 | | Observations, DiagnosticReport |
| medication | 13 | | MedicationRequest, ATC codes |
| demographics | 10 | | Patient-only queries |
| surgery | 6 | | Procedure resource |
| vaccination | 5 | | Immunization resource |
| safety | 5 | | AllergyIntolerance, drug interactions |
| epidemiology | 3 | Yes | Only 3q — all must pass for credibility |

### By Resource Type

| Resource | Count | Notes |
|----------|-------|-------|
| Patient | 64 | Present in most cross-resource queries |
| Condition | 46 | Central to clinical queries |
| MedicationRequest | 18 | ATC codes, prescriptions |
| Observation | 12 | Lab values, vitals |
| CarePlan | 10 | Care coordination, multi-hop |
| Encounter | 9 | Hospitalizations, ambulatory |
| DiagnosticReport | 7 | Lab reports, reference_navigation |
| Procedure | 6 | Surgeries |
| Immunization | 5 | Vaccines |
| AllergyIntolerance | 5 | Allergies, drug safety |

### By Graph Hops

| Hops | Count | Description |
|------|-------|-------------|
| 0 | 43 | Single resource queries |
| 1 | 35 | One reference traversal (e.g., Condition→Patient) |
| 2 | 22 | Two traversals (e.g., Observation→Condition→Patient) |

---

## Questions by Domain

### chronic_disease (28 questions)

The largest domain. Tests terminology resolution (SNOMED CT), patient filtering,
and condition counting — the bread and butter of clinical queries.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S04 | S | 0 | counting | Condition |
| M01 | M | 1 | terminology, counting | Patient+Condition |
| M02 | M | 1 | terminology, counting | Patient+Condition |
| M03 | M | 1 | terminology, counting | Patient+Condition |
| M04 | M | 1 | terminology, counting | Patient+Condition |
| M05 | M | 1 | terminology, counting, filtering | Patient+Condition |
| M06 | M | 1 | terminology, counting | Patient+Condition |
| M07 | M | 0 | counting, filtering | Condition |
| M08 | M | 1 | terminology, counting | Patient+Condition |
| M09 | M | 0 | aggregation, code_execution | Condition |
| M10 | M | 1 | terminology, counting | Patient+Condition |
| M28 | M | 1 | terminology, counting | Patient+Condition |
| M29 | M | 1 | terminology, counting | Patient+Condition |
| M30 | M | 1 | terminology, counting | Patient+Condition |
| M33 | M | 1 | terminology, counting | Patient+Condition |
| M34 | M | 1 | terminology, counting | Patient+Condition |
| C01 | C | 1 | terminology, counting, filtering | Patient+Condition |
| C02 | C | 1 | counting, code_execution | Patient+Condition |
| C04 | C | 1 | terminology, cross_resource, code_execution | Patient+Condition |
| C05 | C | 1 | counting, filtering, cross_resource | Patient+Condition |
| C06 | C | 1 | terminology, aggregation, code_execution | Patient+Condition |
| C12 | C | 2 | terminology, cross_resource | Patient+Condition+MedicationRequest |
| C19 | C | 2 | terminology, cross_resource, filtering | Patient+Condition+MedicationRequest+Observation |
| C23 | C | 0 | counting, temporal | Condition |
| C27 | C | 1 | counting, negation | Patient+Condition |
| C32 | C | 1 | terminology, cross_resource | Patient+Condition |
| C43 | C | 1 | terminology, calculation, code_execution | Patient+Condition |
| C47 | C | 2 | terminology, cross_resource | Patient+Condition+Encounter |

**Key failure patterns to watch:**
- M01-M10: terminology resolution accuracy (wrong SNOMED code = wrong count)
- C01, C05: filtering + terminology combined (two potential failure points)
- C12, C19: multi-hop with 3-4 resources (agent must plan the right traversal)

### care_coordination (16 questions)

Tests CarePlan resource, Encounter types, and multi-resource coordination.
Added in Sprint 5.3. Most complex graph traversals.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S16 | S | 0 | counting | CarePlan |
| M16 | M | 0 | counting, filtering | Encounter |
| M17 | M | 1 | counting, filtering | Patient+Encounter |
| M36 | M | 0 | counting, filtering | CarePlan |
| M37 | M | 1 | counting, cross_resource | Patient+CarePlan |
| M41 | M | 2 | terminology, cross_resource, calculation | Patient+Condition+CarePlan |
| C17 | C | 2 | cross_resource | Patient+Encounter+MedicationRequest |
| C24 | C | 0 | counting, temporal | Encounter |
| C40 | C | 0 | aggregation, code_execution | Encounter |
| C51 | C | 2 | terminology, cross_resource | Patient+Condition+CarePlan |
| C53 | C | 2 | cross_resource, calculation, code_execution | Patient+Condition+CarePlan |
| C56 | C | 2 | terminology, cross_resource, reference_navigation, code_execution | Patient+CarePlan+Condition+MedicationRequest |
| C58 | C | 1 | counting, filtering, temporal | Patient+Encounter |
| C59 | C | 1 | aggregation, reference_navigation, code_execution | CarePlan+Condition |
| C62 | C | 2 | terminology, cross_resource, negation, code_execution | Patient+Condition+CarePlan |
| C64 | C | 2 | cross_resource, negation, code_execution | Patient+Condition+CarePlan |

**Key failure patterns to watch:**
- C17: Encounter class=IMP (hospitalization) filtering — known hard case
- C56: 4-resource traversal, most complex question in the benchmark
- C62: negation + CarePlan status filtering — known hard case
- C51, C53: CarePlan→Condition reference (non-Patient link, unusual in FHIR)

### laboratory (14 questions)

Tests Observation and DiagnosticReport resources. Lab value extraction,
reference navigation (DiagReport→Observation), and calculation.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S11 | S | 0 | counting | DiagnosticReport |
| M11 | M | 0 | terminology, counting | Observation |
| M12 | M | 0 | terminology, counting | Observation |
| M13 | M | 0 | terminology, counting | Observation |
| M18 | M | 0 | terminology, counting | Observation |
| M26 | M | 0 | terminology, counting | DiagnosticReport |
| M27 | M | 0 | terminology, counting | DiagnosticReport |
| M35 | M | 0 | terminology, counting | DiagnosticReport |
| M38 | M | 1 | counting, reference_navigation | DiagnosticReport+Observation |
| M42 | M | 1 | terminology, reference_navigation, counting | DiagnosticReport+Observation |
| C10 | C | 2 | terminology, cross_resource, filtering | Patient+Condition+Observation |
| C13 | C | 2 | terminology, cross_resource, calculation, code_execution | Patient+Condition+Observation |
| C30 | C | 2 | terminology, cross_resource, negation | Patient+Condition+Observation |
| C54 | C | 2 | terminology, cross_resource | Patient+Condition+DiagnosticReport |

**Key failure patterns to watch:**
- M38, M42: DiagnosticReport→Observation reference navigation (non-obvious in FHIR)
- C13: average calculation requires execute_code with correct data extraction
- C30: negation ("patients WITHOUT observations") — tricky logic

### medication (13 questions)

Tests MedicationRequest resource and ATC terminology. Includes negation
patterns and cross-resource drug-condition queries.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| M14 | M | 0 | terminology, counting | MedicationRequest |
| M15 | M | 0 | counting | MedicationRequest |
| M19 | M | 0 | terminology, counting, aggregation | MedicationRequest |
| M20 | M | 0 | counting, filtering | MedicationRequest |
| C08 | C | 2 | terminology, cross_resource | Patient+Condition+MedicationRequest |
| C14 | C | 0 | counting, calculation | MedicationRequest |
| C18 | C | 2 | terminology, cross_resource, reference_navigation | Patient+Condition+MedicationRequest |
| C21 | C | 0 | aggregation, code_execution | MedicationRequest |
| C26 | C | 0 | counting, temporal | MedicationRequest |
| C28 | C | 2 | terminology, cross_resource, negation | Patient+Condition+MedicationRequest |
| C29 | C | 1 | counting, negation | Patient+MedicationRequest |
| C44 | C | 2 | terminology, cross_resource, filtering | Patient+Condition+Observation+MedicationRequest |
| C61 | C | 2 | terminology, cross_resource, filtering, code_execution | Patient+Observation+MedicationRequest |

**Key failure patterns to watch:**
- M14: ATC terminology (metformin A10BA02) — was broken pre-Exp 10
- C28: negation with cross-resource ("diabetes WITHOUT medication")
- C44: 4-resource query (the hardest medication question)
- C61: lab-medication correlation (Observation values + MedicationRequest)

### demographics (10 questions)

All Simple category. Patient resource only. Tests basic FHIR search
parameters (gender, birthDate, address).

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S01 | S | 0 | counting | Patient |
| S02 | S | 0 | counting, filtering | Patient |
| S03 | S | 0 | counting, filtering | Patient |
| S05 | S | 0 | counting, filtering | Patient |
| S06 | S | 0 | counting, filtering | Patient |
| S07 | S | 0 | filtering | Patient |
| S08 | S | 0 | counting, filtering | Patient |
| S12 | S | 0 | counting, filtering | Patient |
| S13 | S | 0 | counting, filtering | Patient |
| S14 | S | 0 | counting, filtering | Patient |

**Key failure patterns to watch:**
- These should ALWAYS pass. Any failure here indicates a fundamental agent problem.
- S07: only "filtering" (no counting) — different output format expected.

### surgery (6 questions)

Tests Procedure resource. Mix of simple counting and complex cross-resource.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S09 | S | 0 | counting | Procedure |
| M21 | M | 0 | aggregation | Procedure |
| M31 | M | 0 | counting, temporal | Procedure |
| M39 | M | 0 | terminology, counting | Procedure |
| C55 | C | 2 | cross_resource, counting, code_execution | Patient+Procedure+Condition |
| C60 | C | 2 | cross_resource, counting, code_execution | Patient+Procedure+Encounter |

**Key failure patterns to watch:**
- C55: "chronic conditions" requires complete list (was broken pre-Exp 10)
- C60: Procedure→Encounter cross-reference

### vaccination (5 questions)

Tests Immunization resource. Temporal filtering and terminology.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S10 | S | 0 | counting | Immunization |
| M24 | M | 1 | terminology, counting | Patient+Immunization |
| M25 | M | 0 | aggregation | Immunization |
| C25 | C | 0 | counting, temporal | Immunization |
| C39 | C | 1 | terminology, cross_resource, filtering | Patient+Immunization |

### safety (5 questions)

Tests AllergyIntolerance resource and drug-allergy cross-checks.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| S15 | S | 0 | counting | AllergyIntolerance |
| M22 | M | 1 | counting | Patient+AllergyIntolerance |
| M32 | M | 0 | terminology, counting | AllergyIntolerance |
| M40 | M | 1 | counting, filtering | Patient+AllergyIntolerance |
| C38 | C | 2 | terminology, cross_resource | Patient+AllergyIntolerance+MedicationRequest |

**Key failure patterns to watch:**
- C38: drug-allergy interaction check — the "safety" showcase question

### epidemiology (3 questions)

**CRITICAL:** Only 3 questions. All must be preserved. Tests geographic
distribution and population-level analysis.

| ID | Cat | Hops | Skills | Resources |
|----|-----|------|--------|-----------|
| C03 | C | 1 | terminology, aggregation, code_execution | Patient+Condition |
| C20 | C | 1 | aggregation, code_execution | Patient+Encounter |
| C42 | C | 1 | terminology, counting, filtering | Patient+Condition |

---

## Disabled Questions (22 total)

### Redundancy-based (19, session 6.1)

Selected for removal because they have the same skill+resource+domain combination
as another kept question. The kept question is listed as "representative."

| ID | Redundant with | Domain | Skills |
|----|---------------|--------|--------|
| C07 | C05 (representative) | chronic_disease | counting, filtering, cross_resource |
| C09 | C08 (representative) | medication | terminology, cross_resource |
| C11 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C15 | C02 (representative) | chronic_disease | counting, code_execution |
| C16 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C31 | C28 (representative) | medication | terminology, cross_resource, negation |
| C33 | C08 (representative) | medication | terminology, cross_resource |
| C34 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C35 | C08 (representative) | medication | terminology, cross_resource |
| C36 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C37 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C41 | C13 (representative) | laboratory | terminology, cross_resource, calculation, code_execution |
| C45 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C48 | C10 (representative) | laboratory | terminology, cross_resource, filtering |
| C49 | C08 (representative) | medication | terminology, cross_resource |
| C50 | C08 (representative) | medication | terminology, cross_resource |
| C52 | C51 (representative) | care_coordination | terminology, cross_resource |
| C57 | C08 (representative) | medication | terminology, cross_resource |
| C63 | C59 (representative) | care_coordination | aggregation, reference_navigation, code_execution |

### Pre-existing (3, sessions 5.2d and earlier)

| ID | Cat | Reason |
|----|-----|--------|
| M23 | M | Ambiguous expected answer (vaccine terminology overlap) |
| C22 | C | Unreliable MedicationRequest dispense counting |
| C46 | C | Vaccine lot number filtering (not supported by seed data) |

---

## How to Use This Document

### After a benchmark run

1. Look at failures by domain → identify which clinical area is weak
2. Look at failures by skill → identify which agent capability needs work
3. Look at failures by graph_hops → 0-hop failures = fundamental, 2-hop = expected difficulty
4. Cross-reference with "Key failure patterns to watch" in each domain section

### Interpreting results across models

- **Simple questions:** All models should score 100%. Failures here indicate broken tool calling or basic FHIR comprehension.
- **Medium questions:** The differentiator for mid-tier models. Terminology resolution accuracy matters most.
- **Complex questions:** Where frontier models separate from smaller ones. Code execution + multi-hop planning.
- **Epidemiology domain:** Only 3 questions — treat as pass/fail signal, not a percentage.

### Priority fix order (when tuning)

1. Fix Simple failures first (agent is fundamentally broken)
2. Fix Medium terminology failures (highest ROI — affects 51 questions)
3. Fix Complex negation/cross_resource failures (hardest, but fewer questions)
4. Fix Complex code_execution failures (often model reasoning, not system issue)
