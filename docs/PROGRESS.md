# SaludAI — Estado Actual

**Última actualización:** 2026-03-04
**Sprint actual:** Sprint 2 — El Cerebro del Agente
**Sesión actual:** 2.4 — Langfuse Integration (completada)

---

## Estado General

🟢 **Sprint 1 completo** — Monorepo configurado, CI activo, Docker Compose con HAPI FHIR R4, FHIR client funcional, repo presentable para público.
🟢 **Sesión 2.1 completa** — TerminologyResolver implementado con SNOMED CT AR (~96 códigos), CIE-10 (~45 códigos), LOINC (~30 códigos). Fuzzy matching con rapidfuzz. 35 tests nuevos, todos verdes.
🟢 **Sesión 2.2 completa** — FHIR Query Builder implementado. Frozen dataclasses para params, fluent builder API, factory shortcuts (snomed, loinc, cie10), soporte para chained params, _include/_revinclude, _sort, _count, _total, _elements. 96 tests nuevos, todos verdes.
🟢 **Sesión 2.3 completa** — Agent Loop v1 implementado en saludai-agent. LLM native tool calling, provider-agnostic (Anthropic/OpenAI/Ollama), 2 tools (resolve_terminology + search_fhir), max iterations cap, bundle summary formatter. 126 tests nuevos (125 nuevos + 1 existente), todos verdes.
🟢 **Sesión 2.4 completa** — Langfuse integration. Tracer protocol + LangfuseTracer + NoOpTracer. Instrumentación explícita del agent loop (generations, tool calls, traces). 29 tests nuevos (155 total agent), todos verdes.

## Última Sesión Completada

**Sprint 2, Sesión 2.4** — Langfuse Integration

### Lo que se hizo
- `saludai_agent/config.py` — Agregado `langfuse_enabled: bool = False`
- `saludai_agent/types.py` — Agregados `trace_id: str | None` y `trace_url: str | None` a `AgentResult`
- `saludai_agent/tracing.py` (NUEVO, ~240 líneas):
  - `Tracer` Protocol (runtime-checkable): `start_trace`, `log_generation`, `log_tool_call`, `end_trace`, `flush`
  - `NoOpTracer` — no-op silencioso cuando tracing deshabilitado
  - `LangfuseTracer` — wraps `langfuse.Langfuse`, crea trace → generations + spans → end
  - `create_tracer(config)` — factory con fallback a NoOpTracer si init falla
  - Helpers: `_summarise_messages()`, `_response_to_dict()`
- `saludai_agent/loop.py` — Instrumentación:
  - `tracer` parámetro opcional en `AgentLoop.__init__` (default NoOpTracer)
  - `start_trace()` al inicio de `run()`
  - `log_generation()` después de cada `llm.generate()`
  - `log_tool_call()` después de cada tool execution
  - `end_trace()` al finalizar (éxito, max iterations, o error)
  - `trace_id`/`trace_url` propagados a `AgentResult`
- `saludai_agent/__init__.py` — Exports: `Tracer`, `LangfuseTracer`, `NoOpTracer`, `create_tracer`
- `scripts/demo_agent.py` — Integrado `create_tracer()`, muestra trace_id/trace_url, `flush()` al final
- Tests: 29 nuevos (test_tracing.py: 22 tests, test_loop.py: 4 tests tracing, 3 tests tipos)
- Trace hierarchy: `agent_run` → `llm_call_N` (generation) + `tool:name` (span)

### Verificación
- `uv run pytest packages/saludai-agent/` → 155 passed
- `uv run pytest packages/saludai-core/` → 150 passed (sin regresión)
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → All files formatted

### Prueba E2E con Langfuse
- `SALUDAI_LANGFUSE_ENABLED=true uv run python scripts/demo_agent.py "Pacientes con diabetes tipo 2"`
- 3 iteraciones, 2 tool calls (resolve_terminology + search_fhir), 15 pacientes encontrados
- Trace visible en Langfuse Cloud con jerarquía completa: agent_run → llm_call_1/2/3 + tool spans
- Python 3.12.10 (bajado de 3.14 por incompatibilidad langfuse/pydantic v1)

## Sprint 1 — Completado

Todas las sesiones del Sprint 1 están finalizadas:
- ✅ 1.1 — Monorepo UV + estructura de paquetes
- ✅ 1.2 — GitHub Actions CI + pre-commit hooks
- ✅ 1.3 — Docker Compose: HAPI FHIR R4 + datos sintéticos argentinos
- ✅ 1.4 — saludai-core: FHIR client (connect, search, read)
- ✅ 1.5 — README, LICENSE, CONTRIBUTING.md

## Sprint 2 — En Progreso

- ✅ 2.1 — Terminology Resolver (SNOMED CT AR, CIE-10, LOINC)
- ✅ 2.2 — FHIR Query Builder
- ✅ 2.3 — Agent Loop v1
- ✅ 2.4 — Langfuse integration
- ⬜ 2.5 — FHIR-AgentBench baseline

## Próxima Sesión

**Sprint:** 2 — El Cerebro del Agente
**Sesión:** 2.5 — FHIR-AgentBench: clonar, setup, primer eval baseline
**Objetivo:** Score baseline documentado, benchmark reproducible
**Referencia:** `docs/ROADMAP.md` → Sprint 2 → Sesión 2.5

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

## Decisiones Pendientes

- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
