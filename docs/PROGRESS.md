# SaludAI — Estado Actual

**Última actualización:** 2026-03-04
**Sprint actual:** Sprint 2 — El Cerebro del Agente
**Sesión actual:** 2.3 — Agent Loop v1 (completada)

---

## Estado General

🟢 **Sprint 1 completo** — Monorepo configurado, CI activo, Docker Compose con HAPI FHIR R4, FHIR client funcional, repo presentable para público.
🟢 **Sesión 2.1 completa** — TerminologyResolver implementado con SNOMED CT AR (~96 códigos), CIE-10 (~45 códigos), LOINC (~30 códigos). Fuzzy matching con rapidfuzz. 35 tests nuevos, todos verdes.
🟢 **Sesión 2.2 completa** — FHIR Query Builder implementado. Frozen dataclasses para params, fluent builder API, factory shortcuts (snomed, loinc, cie10), soporte para chained params, _include/_revinclude, _sort, _count, _total, _elements. 96 tests nuevos, todos verdes.
🟢 **Sesión 2.3 completa** — Agent Loop v1 implementado en saludai-agent. LLM native tool calling, provider-agnostic (Anthropic/OpenAI/Ollama), 2 tools (resolve_terminology + search_fhir), max iterations cap, bundle summary formatter. 126 tests nuevos (125 nuevos + 1 existente), todos verdes.

## Última Sesión Completada

**Sprint 2, Sesión 2.3** — Agent Loop v1

### Lo que se hizo
- `saludai_agent/exceptions.py` — Jerarquía: AgentError, AgentLoopError, ToolExecutionError, LLMError, LLMResponseError
- `saludai_agent/config.py` — AgentConfig con pydantic-settings (llm_provider, llm_model, llm_api_key, llm_base_url, agent_max_iterations, agent_max_tokens, agent_temperature)
- `saludai_agent/types.py` — Frozen dataclasses: Message, ToolCall, ToolResult, TokenUsage, LLMResponse, AgentResult
- `saludai_agent/prompts.py` — System prompt en español para agente FHIR argentino + PROMPT_VERSION
- `saludai_agent/llm.py` — LLMClient Protocol + AnthropicLLMClient + OpenAILLMClient + create_llm_client factory
  - Conversión bidireccional Message ↔ Anthropic API / OpenAI API
  - Soporte Ollama via OpenAI client con base_url
- `saludai_agent/tools.py` — ToolRegistry + 2 tools:
  - `resolve_terminology` — wraps TerminologyResolver.resolve()
  - `search_fhir` — wraps FHIRClient.search() + format_bundle_summary()
  - `format_bundle_summary()` — extrae campos clave por resource type para summaries token-efficient
- `saludai_agent/loop.py` — AgentLoop class:
  - Dependency injection (LLMClient, FHIRClient, TerminologyResolver, AgentConfig)
  - Tool-calling loop: send → execute tools → repeat → return narrative
  - Max iterations cap (default 5), tool errors returned to LLM gracefully
- `saludai_agent/__init__.py` — Exports completos
- `pyproject.toml` — Agregadas dependencias structlog, pydantic-settings
- Tests: 7 archivos, 126 tests en 20+ clases (exceptions, config, types, prompts, llm, tools, loop)

### Verificación
- `uv run pytest packages/saludai-agent/` → 126 passed
- `uv run pytest packages/saludai-core/` → 131 passed (sin regresión)
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → All files formatted

### Prueba end-to-end
- `scripts/demo_agent.py` — script de demo contra HAPI FHIR + Claude Sonnet
- Query "Pacientes con diabetes tipo 2" → 3 iteraciones, 2 tool calls, respuesta correcta con 15 pacientes
- Query "Medicaciones activas" → 2 iteraciones, 1 tool call, respuesta correcta (sin datos en seed)

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
- ⬜ 2.4 — Langfuse integration
- ⬜ 2.5 — FHIR-AgentBench baseline

## Próxima Sesión

**Sprint:** 2 — El Cerebro del Agente
**Sesión:** 2.4 — Langfuse integration + Docker Compose actualizado
**Objetivo:** Traces visibles en Langfuse para cada paso del agent loop
**Referencia:** `docs/ROADMAP.md` → Sprint 2 → Sesión 2.4

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
