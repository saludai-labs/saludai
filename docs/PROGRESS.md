# SaludAI — Estado Actual

**Última actualización:** 2026-03-04
**Sprint actual:** Sprint 3 — Multi-turn y Precisión
**Sesión actual:** 3.2 — Reference Navigator + Fixes (completada)

---

## Estado General

🟢 **Sprint 1 completo** — Monorepo configurado, CI activo, Docker Compose con HAPI FHIR R4, FHIR client funcional, repo presentable para público.
🟢 **Sesión 2.1 completa** — TerminologyResolver implementado con SNOMED CT AR (~96 códigos), CIE-10 (~45 códigos), LOINC (~30 códigos). Fuzzy matching con rapidfuzz. 35 tests nuevos, todos verdes.
🟢 **Sesión 2.2 completa** — FHIR Query Builder implementado. Frozen dataclasses para params, fluent builder API, factory shortcuts (snomed, loinc, cie10), soporte para chained params, _include/_revinclude, _sort, _count, _total, _elements. 96 tests nuevos, todos verdes.
🟢 **Sesión 2.3 completa** — Agent Loop v1 implementado en saludai-agent. LLM native tool calling, provider-agnostic (Anthropic/OpenAI/Ollama), 2 tools (resolve_terminology + search_fhir), max iterations cap, bundle summary formatter. 126 tests nuevos (125 nuevos + 1 existente), todos verdes.
🟢 **Sesión 2.4 completa** — Langfuse integration. Tracer protocol + LangfuseTracer + NoOpTracer. Instrumentación explícita del agent loop (generations, tool calls, traces). 29 tests nuevos (155 total agent), todos verdes.
🟢 **Sesión 2.5 completa** — FHIR-AgentBench baseline. Framework de evaluación con 25 preguntas curadas, LLM-as-judge, métricas por categoría. Baseline: **88% accuracy** (22/25). 30 tests nuevos (337 total), todos verdes.
🟢 **Sesión 2.6 completa** — Benchmark honesto + Documento de Experimentos. Seed enriquecido (536 entries, 5 resource types), 50 preguntas (8 simple, 20 medium, 22 complex), judge híbrido (programmatic + Haiku), fix MedicationRequest parsing. **Baseline honesto: 60% accuracy** (30/50). 8 tests nuevos (374 total), todos verdes.
🟢 **Sesión 3.1 completa** — Pagination + `_summary=count`. Default `_count=200`, `SummaryMode` enum, format summary-count bundles, system prompt con estrategia de consulta. **Accuracy: 82.0%** (41/50). 355 tests, todos verdes.
🟢 **Sesión 3.2 completa** — Reference Navigator + Fixes. Terminology disambiguation fix, nuevo tool `get_resource`, max_iterations 5→8, system prompt v1.2 con guidance de `_include`/`_revinclude`. **Accuracy: 86.0%** (43/50, 0 errors). 365 tests, todos verdes.
🟢 **Sesión 3.3 completa** — Code Interpreter tool. Sandbox Python execution para conteo/agrupación. **Accuracy: 94.0%** (47/50, 1 error). 391 tests, todos verdes.

## Última Sesión Completada

**Sprint 3, Sesión 3.3** — Code Interpreter

### Lo que se hizo
- `packages/saludai-agent/src/saludai_agent/tools.py`:
  - `EXECUTE_CODE_DEFINITION` — tool definition para ejecución de Python sandboxeado
  - `execute_code()` — executor con sandbox (builtins restringidos, `_restricted_import`, timeout, output truncation)
  - Módulos pre-importados: json, collections, datetime, math, statistics, re
  - `ToolRegistry.__init__()` — registra `execute_code` (siempre disponible)
- `packages/saludai-agent/src/saludai_agent/prompts.py` — `PROMPT_VERSION = "v1.3"`, tool #4 `execute_code`, sección "Procesamiento de datos"
- Tests: 26 tests nuevos (execute_code definition×3, executor×17, registry×1, prompts×2, registry assertions×2 actualizados)

### Resultados del Benchmark (Exp 4)
- **Accuracy total: 94.0%** (47/50 correctas) — +8pp vs Exp 3
- Simple: 8/8 (100%)
- Medium: 19/20 (95%)
- Complex: 20/22 (91%) — +18pp vs Exp 3
- Errors: 1 (C05 timeout)
- Incorrect: 2 (M07, C14 — non-determinism)
- Avg duration: 33.7s por pregunta
- Avg iterations: 3.5
- Agent: Claude Sonnet 4.5
- Judge: Claude Haiku 4.5 (híbrido)

### Fallas restantes (3)
- **M07** (medium): non-determinism (pasa/falla entre corridas)
- **C05** (complex): timeout (120s) — query compleja con muchos datos
- **C14** (complex): non-determinism (pasa/falla entre corridas)

### Verificación
- `uv run pytest` → 391 passed
- `uv run ruff check .` → All checks passed
- `uv run python -m benchmarks.run_eval` → 94% accuracy (1 error)

## Sprint 1 — Completado

Todas las sesiones del Sprint 1 están finalizadas:
- ✅ 1.1 — Monorepo UV + estructura de paquetes
- ✅ 1.2 — GitHub Actions CI + pre-commit hooks
- ✅ 1.3 — Docker Compose: HAPI FHIR R4 + datos sintéticos argentinos
- ✅ 1.4 — saludai-core: FHIR client (connect, search, read)
- ✅ 1.5 — README, LICENSE, CONTRIBUTING.md

## Sprint 2 — Completado

- ✅ 2.1 — Terminology Resolver (SNOMED CT AR, CIE-10, LOINC)
- ✅ 2.2 — FHIR Query Builder
- ✅ 2.3 — Agent Loop v1
- ✅ 2.4 — Langfuse integration
- ✅ 2.5 — FHIR-AgentBench baseline (88%, inflado)
- ✅ 2.6 — Benchmark Honesto + Documento de Experimentos (60%, baseline real)

## Sprint 3 — En Progreso

- ✅ 3.1 — Pagination + `_summary=count` (60% → 82%)
- ✅ 3.2 — Reference Navigator + Fixes (82% → 86%, 0 errors)
- ✅ 3.3 — Code Interpreter (86% → 94%, +8pp)

## Próxima Sesión

**Sprint:** 3 — Multi-turn y Precisión
**Sesión:** 3.4 — AR Profile Validator + mejoras terminology
**Objetivo:** Validación contra perfiles openRSD, mejoras de terminología
**Referencia:** `docs/ROADMAP.md` → Sprint 3 → Sesión 3.4
**Fallas restantes (Exp 4):** 2 non-determinism (M07, C14), 1 timeout (C05)

## Blockers

Ninguno.

## Decisiones Tomadas

- GitHub Org: `saludai-labs` (confirmado)
- Git remote via HTTPS (no SSH)
- Root pyproject.toml es workspace virtual (sin build-system)
- `dependency-groups.dev` para dev-dependencies (estándar actual de UV)
- CI: Python 3.12 single version (sin matrix — no agrega valor todavía)
- CI: Sin mypy por ahora (no hay código real que tipar)
- CI: Sin coverage enforcement (no hay tests sustanciales)
- Pre-commit: `ruff-pre-commit` oficial (no ruff via sistema)
- Pytest: `--import-mode=importlib` para monorepos con test files homónimos
- **Langfuse Cloud (free tier)** en vez de self-hosted (ADR-006)
- **HAPI FHIR con H2 en memoria** — datos efímeros, sin PostgreSQL extra
- **fhir.resources default** — compatible con R4, sin sub-módulo específico
- **TerminologyResolver sync** — todo es CPU en memoria, no necesita async
- **CSVs embebidos** — legibles, diffeables, editables por no-programadores
- **rapidfuzz** — ~10x más rápido que difflib, provee token_sort_ratio + partial_ratio
- **Scores 0-100** — consistente con escala de rapidfuzz (EXACT_MATCH_SCORE = 100.0)
- **No stripear acentos** — rapidfuzz maneja variantes naturalmente
- **QueryBuilder puramente sync** — solo transforma datos, no hace I/O
- **Frozen dataclasses** para todos los param types — inmutabilidad garantizada
- **Factory shortcuts** (snomed, loinc, cie10) — ergonomía sin perder tipado
- **validate=False escape hatch** — permite resource types custom sin romper API
- **LLM-as-judge** para benchmark — evaluación binaria CORRECT/INCORRECT, tolerante a formato

## Decisiones Pendientes

- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
