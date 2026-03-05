# SaludAI — Estado Actual

**Ultima actualizacion:** 2026-03-05
**Sprint actual:** Sprint 4 — Producto y Lanzamiento
**Sesion actual:** 4.4 — Jupyter notebooks + README final (completada)

---

## Estado General

🟢 **Sprint 1 completo** — Monorepo configurado, CI activo, Docker Compose con HAPI FHIR R4, FHIR client funcional, repo presentable para publico.
🟢 **Sesion 2.1 completa** — TerminologyResolver implementado con SNOMED CT AR (~96 codigos), CIE-10 (~45 codigos), LOINC (~30 codigos). Fuzzy matching con rapidfuzz. 35 tests nuevos, todos verdes.
🟢 **Sesion 2.2 completa** — FHIR Query Builder implementado. Frozen dataclasses para params, fluent builder API, factory shortcuts (snomed, loinc, cie10), soporte para chained params, _include/_revinclude, _sort, _count, _total, _elements. 96 tests nuevos, todos verdes.
🟢 **Sesion 2.3 completa** — Agent Loop v1 implementado en saludai-agent. LLM native tool calling, provider-agnostic (Anthropic/OpenAI/Ollama), 2 tools (resolve_terminology + search_fhir), max iterations cap, bundle summary formatter. 126 tests nuevos (125 nuevos + 1 existente), todos verdes.
🟢 **Sesion 2.4 completa** — Langfuse integration. Tracer protocol + LangfuseTracer + NoOpTracer. Instrumentacion explicita del agent loop (generations, tool calls, traces). 29 tests nuevos (155 total agent), todos verdes.
🟢 **Sesion 2.5 completa** — FHIR-AgentBench baseline. Framework de evaluacion con 25 preguntas curadas, LLM-as-judge, metricas por categoria. Baseline: **88% accuracy** (22/25). 30 tests nuevos (337 total), todos verdes.
🟢 **Sesion 2.6 completa** — Benchmark honesto + Documento de Experimentos. Seed enriquecido (536 entries, 5 resource types), 50 preguntas (8 simple, 20 medium, 22 complex), judge hibrido (programmatic + Haiku), fix MedicationRequest parsing. **Baseline honesto: 60% accuracy** (30/50). 8 tests nuevos (374 total), todos verdes.
🟢 **Sesion 3.1 completa** — Pagination + `_summary=count`. Default `_count=200`, `SummaryMode` enum, format summary-count bundles, system prompt con estrategia de consulta. **Accuracy: 82.0%** (41/50). 355 tests, todos verdes.
🟢 **Sesion 3.2 completa** — Reference Navigator + Fixes. Terminology disambiguation fix, nuevo tool `get_resource`, max_iterations 5→8, system prompt v1.2 con guidance de `_include`/`_revinclude`. **Accuracy: 86.0%** (43/50, 0 errors). 365 tests, todos verdes.
🟢 **Sesion 3.3 completa** — Code Interpreter tool. Sandbox Python execution para conteo/agrupacion. **Accuracy: 94.0%** (47/50, 1 error). 391 tests, todos verdes.
🟢 **Sesion 3.4a completa** — Limpieza de deuda tecnica. ADRs 002, 004, 005. Coverage config (84.57%). CI con coverage.
🟢 **Sesion 3.4b completa** — Sistema de locale packs. Extensibilidad por pais/region. 375 tests, todos verdes.
🟢 **Sesion 3.5 completa** — Judge fix + re-eval. **Accuracy: 98.0%** (49/50). 375 tests, todos verdes.
🟢 **Sesion 3.6 completa** — FHIR Awareness en locale packs. 6 tipos nuevos, AR pack con datos openRSD reales, prompt dinamico, ADR-008. 449 tests, todos verdes.
🟢 **Sesion 4.1 completa** — MCP Server. FastMCP con 4 tools, lifespan, CLI entry point. 466 tests, todos verdes.

## Ultima Sesion Completada

**Sprint 4, Sesion 4.7** — Locale pack discovery via `entry_points`

### Lo que se hizo
- **Entry-point discovery** — `load_locale_pack()` ahora busca packs externos en `importlib.metadata.entry_points(group="saludai.locales")` como fallback despues de los built-in.
- **`available_locales()` expandido** — retorna built-in + entry points registrados.
- **Validacion** — entry points que no son `LocalePack` lanzan `LocaleNotFoundError` con mensaje descriptivo.
- **Built-in priority** — packs built-in (`"ar"`) siempre ganan sobre entry points con el mismo codigo.
- **6 tests nuevos** — `TestEntryPointDiscovery` cubre: discovery, prioridad, invalidez, not-found, available_locales, error message.
- **`LOCALE_GUIDE.md` actualizado** — seccion "Registrar via entry points" con instrucciones de `pyproject.toml`.

### Verificacion
- `uv run ruff check .` → All checks passed
- `uv run pytest --no-cov` → 479 passed, 11 skipped

## Sprint 1 — Completado

Todas las sesiones del Sprint 1 estan finalizadas:
- ✅ 1.1 — Monorepo UV + estructura de paquetes
- ✅ 1.2 — GitHub Actions CI + pre-commit hooks
- ✅ 1.3 — Docker Compose: HAPI FHIR R4 + datos sinteticos argentinos
- ✅ 1.4 — saludai-core: FHIR client (connect, search, read)
- ✅ 1.5 — README, LICENSE, CONTRIBUTING.md

## Sprint 2 — Completado

- ✅ 2.1 — Terminology Resolver (SNOMED CT AR, CIE-10, LOINC)
- ✅ 2.2 — FHIR Query Builder
- ✅ 2.3 — Agent Loop v1
- ✅ 2.4 — Langfuse integration
- ✅ 2.5 — FHIR-AgentBench baseline (88%, inflado)
- ✅ 2.6 — Benchmark Honesto + Documento de Experimentos (60%, baseline real)

## Sprint 3 — Completado

- ✅ 3.1 — Pagination + `_summary=count` (60% → 82%)
- ✅ 3.2 — Reference Navigator + Fixes (82% → 86%, 0 errors)
- ✅ 3.3 — Code Interpreter (86% → 94%, +8pp)
- ✅ 3.4a — Limpieza de deuda tecnica (ADRs, coverage config)
- ✅ 3.4b — Sistema de locale packs (extensibilidad por pais/region)
- ✅ 3.5 — Judge fix + re-eval benchmark (94% → 98%)
- ✅ 3.6 — FHIR Awareness en locale packs (Level 1)

## Sprint 4 — En progreso

- ✅ 4.1 — MCP Server (FastMCP, 4 tools, CLI entry point, 17 tests)
- ✅ 4.2 — REST API `/query` + CLI `saludai query` (agent loop via HTTP y terminal)
- ✅ 4.3 — PyPI packaging + Docker image (meta-paquete, Dockerfile, CI publish)
- ✅ 4.4 — 3 Jupyter notebooks + README final con badges
- [ ] 4.5 — Blog post + video demo 5 min
- ✅ 4.6 — Quick wins: limpiar data/, licencia datos, `execute(query)` [S]
- ✅ 4.7 — Locale pack discovery via `entry_points` [M]
- [ ] 4.8 — Parámetro `_has` (reverse chaining) en Query Builder [M]
- [ ] 4.9 — FHIR Awareness Level 2: validación y ejecución [L]

## Proxima Sesion

**Sprint:** 4 — Producto y Lanzamiento
**Sesion:** 4.8 — Parametro `_has` (reverse chaining) en Query Builder
**Objetivo:** Soporte de `_has` en el query builder para consultas complejas
**Referencia:** `docs/ROADMAP.md` → Sprint 4 → Sesion 4.8
**Fallas restantes (Exp 5):** 1 max iterations (C05)
**Pendiente:** 4.5 (blog/video), 4.8-4.9 (backlog tecnico)

## Blockers

Ninguno.

## Decisiones Tomadas

- GitHub Org: `saludai-labs` (confirmado)
- Git remote via HTTPS (no SSH)
- Root pyproject.toml es workspace virtual (sin build-system)
- `dependency-groups.dev` para dev-dependencies (estandar actual de UV)
- CI: Python 3.12 single version (sin matrix — no agrega valor todavia)
- CI: Sin mypy por ahora (no hay codigo real que tipar)
- CI: Sin coverage enforcement (no hay tests sustanciales)
- Pre-commit: `ruff-pre-commit` oficial (no ruff via sistema)
- Pytest: `--import-mode=importlib` para monorepos con test files homonimos
- **Langfuse Cloud (free tier)** en vez de self-hosted (ADR-006)
- **HAPI FHIR con H2 en memoria** — datos efimeros, sin PostgreSQL extra
- **fhir.resources default** — compatible con R4, sin sub-modulo especifico
- **TerminologyResolver sync** — todo es CPU en memoria, no necesita async
- **CSVs embebidos** — legibles, diffeables, editables por no-programadores
- **rapidfuzz** — ~10x mas rapido que difflib, provee token_sort_ratio + partial_ratio
- **Scores 0-100** — consistente con escala de rapidfuzz (EXACT_MATCH_SCORE = 100.0)
- **No stripear acentos** — rapidfuzz maneja variantes naturalmente
- **QueryBuilder puramente sync** — solo transforma datos, no hace I/O
- **Frozen dataclasses** para todos los param types — inmutabilidad garantizada
- **Factory shortcuts** (snomed, loinc, cie10) — ergonomia sin perder tipado
- **validate=False escape hatch** — permite resource types custom sin romper API
- **LLM-as-judge** para benchmark — evaluacion binaria CORRECT/INCORRECT, tolerante a formato
- **FHIR Awareness Level 1** — metadata declarativa en locale packs (ADR-008)

## Decisiones Pendientes

- [x] ~~Licencia datos sinteticos~~ → Apache 2.0 (misma que el proyecto). Datos Synthea son Apache 2.0, CSVs de terminologia son compilaciones de estandares publicos.
