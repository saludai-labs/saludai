# SaludAI — Estado Actual

**Última actualización:** 2026-03-04
**Sprint actual:** Sprint 3 — Multi-turn y Precisión
**Sesión actual:** 3.1 — Pagination + `_summary=count` (completada)

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

## Última Sesión Completada

**Sprint 3, Sesión 3.1** — Pagination + `_summary=count`

### Lo que se hizo
- `packages/saludai-core/src/saludai_core/query_builder.py` — `SummaryMode` enum + `.summary()` method en `FHIRQueryBuilder`
- `packages/saludai-core/src/saludai_core/__init__.py` — Re-export `SummaryMode`
- `packages/saludai-agent/src/saludai_agent/tools.py`:
  - `execute_search_fhir()` — inyecta `_count=200` por defecto (no sobreescribe si hay `_count` o `_summary` explícito)
  - `format_bundle_summary()` — maneja bundles `_summary=count` (total > 0 sin entries → "Total count: N")
  - `SEARCH_FHIR_DEFINITION` — descripción de params actualizada con `_summary` y `_count`
- `packages/saludai-agent/src/saludai_agent/prompts.py` — Sección "Estrategia de consulta" en SYSTEM_PROMPT, `PROMPT_VERSION = "v1.1"`
- Tests: 5 tests nuevos en test_tools.py (summary-count format, _count injection, no-override), 5 tests nuevos en test_query_builder.py (.summary() con string/enum/invalid/combined), 1 fix test_prompts.py (version bump)

### Resultados del Benchmark (Exp 2)
- **Accuracy total: 82.0%** (41/50 correctas)
- Simple: 8/8 (100%) — +50pp vs Exp 1
- Medium: 16/20 (80%) — +20pp vs Exp 1
- Complex: 17/22 (77%) — +13pp vs Exp 1
- Errors: 4 (API retries/timeouts)
- Incorrect: 5
- Avg duration: 16.1s por pregunta
- Avg iterations: 2.8
- Agent: Claude Sonnet 4.5
- Judge: Claude Haiku 4.5 (híbrido)

### Verificación
- `uv run pytest` → 355 passed
- `uv run ruff check .` → All checks passed
- `uv run python -m benchmarks.run_eval` → 82% accuracy

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

## Próxima Sesión

**Sprint:** 3 — Multi-turn y Precisión
**Sesión:** 3.2 — Reference Navigator (resolve refs, multi-hop)
**Objetivo:** Mejorar navegación de referencias entre recursos (MedicationRequest → Patient → Conditions)
**Referencia:** `docs/ROADMAP.md` → Sprint 3 → Sesión 3.2
**Fallas restantes (Exp 2):** 5 INCORRECT + 4 ERRORS — analizar patrones para priorizar siguiente mejora

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
