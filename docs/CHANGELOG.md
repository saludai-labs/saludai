# SaludAI — Changelog

Registro de cambios por sesión de desarrollo.

---

## [Sprint 3, Sesión 3.1] — 2026-03-04

### Pagination + `_summary=count`

**Core — QueryBuilder:**
- Agregado `SummaryMode` enum (TRUE, TEXT, DATA, COUNT, FALSE) a `query_builder.py`
- Agregado método `.summary(mode)` al `FHIRQueryBuilder` con validación
- Actualizado `__init__.py` con re-export de `SummaryMode`

**Agent — Pagination fix:**
- `execute_search_fhir()` inyecta `_count=200` por defecto cuando no hay `_count` ni `_summary` explícito
- `format_bundle_summary()` maneja bundles `_summary=count`: `{total: N}` sin entries → "Total count: N (summary-only, no individual entries returned)."
- Bundles vacíos sin total → "No results found." (sin "(total: 0)" confuso)

**Agent — Prompt & tool description:**
- `SEARCH_FHIR_DEFINITION` params description actualizada con `_summary: "count"` y `_count: "200"`
- `SYSTEM_PROMPT` con nueva sección "Estrategia de consulta" (cuándo usar `_summary: "count"` vs datos completos)
- `PROMPT_VERSION` bumped a `"v1.1"`

**Tests:**
- 5 tests nuevos en `test_tools.py`: summary-count bundle format (total>0, total=0, no-total), `_count` default injection, no-override con `_count`/`_summary` explícito
- 5 tests nuevos en `test_query_builder.py`: `.summary()` con string, enum, valor inválido, combined con otros params
- Fix `test_prompts.py`: version assertion actualizada a v1.1
- Total: 355 tests, todos verdes

**Benchmark (Exp 2):**
- **Accuracy: 82.0%** (41/50) — +22pp vs 60% (Exp 1)
- Simple: 8/8 (100%) — +50pp
- Medium: 16/20 (80%) — +20pp
- Complex: 17/22 (77%) — +13pp
- 4 errores por API retries/timeouts, 5 incorrectas
- Avg duration: 16.1s, avg iterations: 2.8

---

## [Sprint 2, Sesión 2.6] — 2026-03-04

### Benchmark Honesto + Documento de Experimentos

**Seed data enriquecido:**
- Agregados 2 LOINC codes a `loinc.csv`: PA sistólica (8480-6), PA diastólica (8462-4)
- Enriquecido `generate_seed_data.py` con 3 nuevos resource types:
  - Observations (163): 6 tipos LOINC, valores correlacionados con condiciones
  - MedicationRequests (116): 10 medicamentos ATC, correlacionados con condiciones
  - Encounters (122): 4 tipos (AMB 55%, EMER 20%, IMP 15%, HH 10%)
- Regenerado `seed_bundle.json`: 536 entries total (55 + 80 + 163 + 116 + 122)
- Actualizado `seed.sh` con verificación de nuevos resource types

**Benchmark expandido:**
- Expandido `dataset.json` de 25 a 50 preguntas (8 simple, 20 medium, 22 complex)
- Endurecidos criterios de aceptación usando números exactos del seed
- Nuevas subcategorías: observation_query, medication_query, encounter_query, cross_resource, calculation, reference_traversal, advanced_aggregation

**Judge mejorado:**
- Cambiado judge de Claude Sonnet a Claude Haiku 4.5 (reducción de costo)
- Agregado pre-check programático para rangos numéricos (determinístico, sin costo LLM)
- Fix markdown fence parsing para Haiku (`_strip_markdown_fences()`)
- 8 tests nuevos para numeric range check

**Fixes:**
- `fhir_client.py`: `search()` retorna raw dict en vez de parsear con fhir.resources (fix MedicationRequest choice-type fields)
- `tools.py`: `format_bundle_summary()` reescrito para manejar dicts + objects, soporte Encounter class/period, server total display
- Tests actualizados: test_fhir_client.py (dict access), test_tools.py (dict fixtures)

**Documentación:**
- Creado `docs/experiments/EXPERIMENTS.md` — documento formal de experimentos (Exp 0-4)
- Actualizado `docs/knowledge/README.md` con link a experiments
- Actualizado `README.md` con score honesto (60%)

**Resultado: 60.0% accuracy** (30/50) — Simple 50%, Medium 60%, Complex 64%. Pagination es el blocker principal.
- Verificación: 374 tests (336 package + 38 benchmark), ruff limpio

---

## [Sprint 2, Sesión 2.5] — 2026-03-04

### FHIR-AgentBench Baseline (benchmarks/)
- Creado `benchmarks/config.py` — BenchmarkConfig con pydantic-settings (SALUDAI_BENCH_ prefix)
- Creado `benchmarks/dataset.py` — EvalQuestion frozen dataclass + load_dataset() con validación
- Creado `benchmarks/dataset.json` — 25 preguntas curadas contra seed data:
  - 8 simple (conteos, demografía, existencia)
  - 10 medium (terminology resolution + filtros combinados)
  - 7 complex (multi-resource, comorbilidad, agregación geográfica)
- Creado `benchmarks/judge.py` — AnswerJudge con LLM-as-judge:
  - Evaluación binaria CORRECT/INCORRECT
  - Tolerante a formato, estricta en facts
  - Fallback a INCORRECT si parseo JSON falla
- Creado `benchmarks/metrics.py` — BenchmarkMetrics + CategoryMetrics + compute_metrics()
- Creado `benchmarks/results.py` — QuestionResult + write_results_json() + print_summary()
- Creado `benchmarks/harness.py` — EvalHarness: orquesta agent + judge secuencialmente, timeout por pregunta
- Creado `benchmarks/run_eval.py` — CLI con argparse: --category, --question, --output-dir
- Creado `benchmarks/__main__.py` — soporte para `python -m benchmarks`
- Creados 30 tests en 4 archivos:
  - test_dataset (9): carga, IDs únicos, categorías, campos, custom path, errores
  - test_judge (8): correct/incorrect/malformed/empty, notes, lowercase verdict
  - test_metrics (9): empty/correct/incorrect/mixed/errors, avg duration/iterations, categories
  - test_results (4): output file, directories, UTF-8, print_summary
- Actualizado `pyproject.toml` — benchmarks en testpaths y known-first-party
- Actualizado `.gitignore` — benchmarks/results/ excluido
- Actualizado `README.md` — sección Benchmark con tabla de scores
- **Baseline: 88.0% accuracy** (22/25) — Simple 88%, Medium 100%, Complex 71%
- Verificación: 30 benchmark tests + 307 package tests = 337 total, ruff limpio

---

## [Sprint 2, Sesión 2.4] — 2026-03-04

### Langfuse Integration (saludai-agent)
- Agregado `langfuse_enabled: bool = False` a `AgentConfig`
- Agregados `trace_id: str | None` y `trace_url: str | None` a `AgentResult`
- Creado `saludai_agent/tracing.py` (~240 líneas):
  - `Tracer` Protocol (runtime-checkable)
  - `NoOpTracer` — no-op cuando tracing deshabilitado
  - `LangfuseTracer` — wraps langfuse.Langfuse, genera trace → generations/spans
  - `create_tracer(config)` — factory con fallback a NoOpTracer
  - Helpers: `_summarise_messages()`, `_response_to_dict()`
- Instrumentado `AgentLoop.run()`:
  - `start_trace()` al inicio, `log_generation()` por cada LLM call
  - `log_tool_call()` por cada tool execution, `end_trace()` al finalizar
  - `trace_id`/`trace_url` propagados a `AgentResult`
  - `end_trace()` también en error paths (max iterations, exceptions)
- Actualizado `__init__.py` — exports de Tracer, LangfuseTracer, NoOpTracer, create_tracer
- Actualizado `scripts/demo_agent.py` — integrado tracer, muestra trace_id/trace_url
- Creado `tests/test_tracing.py` — 22 tests (NoOpTracer, LangfuseTracer, create_tracer, helpers)
- Agregados 4 tests de tracing a `test_loop.py`
- Verificación: 155 agent tests + 150 core tests = 305 total, ruff limpio, format limpio

---

## [Sprint 2, Sesión 2.3] — 2026-03-04

### Agent Loop v1 (saludai-agent)
- Creada jerarquía de excepciones: `AgentError`, `AgentLoopError`, `ToolExecutionError`, `LLMError`, `LLMResponseError`
- Creado `saludai_agent/config.py` — `AgentConfig` con pydantic-settings (7 campos, env prefix SALUDAI_)
- Creado `saludai_agent/types.py` — frozen dataclasses: `Message`, `ToolCall`, `ToolResult`, `TokenUsage`, `LLMResponse`, `AgentResult`
- Creado `saludai_agent/prompts.py` — system prompt en español para agente FHIR argentino + `PROMPT_VERSION = "v1.0"`
- Creado `saludai_agent/llm.py` (~400 líneas):
  - `LLMClient` Protocol (runtime-checkable)
  - `AnthropicLLMClient` — usa `anthropic.AsyncAnthropic`, convierte Message ↔ Anthropic API
  - `OpenAILLMClient` — usa `openai.AsyncOpenAI`, compatible con OpenAI y Ollama (via base_url)
  - `create_llm_client(config)` — factory function
- Creado `saludai_agent/tools.py` (~300 líneas):
  - Tool definitions en formato Anthropic (JSON schema) — `resolve_terminology`, `search_fhir`
  - `execute_resolve_terminology()` — wraps TerminologyResolver.resolve()
  - `execute_search_fhir()` — wraps FHIRClient.search()
  - `format_bundle_summary()` — extrae campos clave por resource type, genera texto conciso
  - `ToolRegistry` — holds definitions + executors, `definitions()`, `execute(tool_call)`
- Creado `saludai_agent/loop.py` (~120 líneas):
  - `AgentLoop` — dependency injection, tool-calling loop, max iterations cap
  - Tool errors gracefully returned to LLM (no crash)
- Actualizado `__init__.py` — exports de AgentLoop, AgentResult, AgentConfig, LLMClient, etc.
- Actualizado `pyproject.toml` — agregadas dependencias `structlog>=24`, `pydantic-settings>=2`
- Creados 7 archivos de test, 126 tests en 20+ clases:
  - test_exceptions (10), test_config (17), test_types (17), test_prompts (12), test_llm (22), test_tools (23), test_loop (16), test_init (1)
- Verificación: 126 agent tests + 131 core tests = 257 total, ruff limpio, format limpio
- Creado `scripts/demo_agent.py` — script de prueba end-to-end contra HAPI FHIR + Claude
- AgentConfig: `extra="ignore"` para coexistir con .env compartido entre paquetes
- Prueba exitosa: "Pacientes con diabetes tipo 2" → resolve_terminology + search_fhir → respuesta correcta

---

## [Sprint 2, Sesión 2.2] — 2026-03-03

### FHIR Query Builder
- Extendida jerarquía de excepciones: `QueryBuilderError`, `QueryBuilderValidationError`
- Creado `saludai_core/query_builder.py` (~400 líneas) — módulo principal:
  - Enums: `FHIRResourceType` (15 resource types), `DatePrefix` (8 prefijos), `SortOrder`
  - Frozen dataclasses: `TokenParam`, `DateParam`, `ReferenceParam`, `QuantityParam`, `StringParam`, `IncludeParam`, `SortParam` — todos con `to_fhir() -> str`
  - `FHIRQuery` — output inmutable con `to_params() -> dict[str, str | list[str]]` compatible con `FHIRClient.search()`
  - Factory functions: `token()`, `snomed()`, `loinc()`, `cie10()`, `date_param()`, `reference()`, `quantity()`
  - `FHIRQueryBuilder` — API fluent con `where()`, `where_token()`, `where_date()`, `where_reference()`, `where_string()`, `include()`, `revinclude()`, `sort()`, `count()`, `total()`, `elements()`, `build()`
  - Validación: resource types contra enum (con escape hatch `validate=False`), formato ISO 8601, params no vacíos, `_count` positivo, `_total` en {none, estimate, accurate}
  - Constantes: `SNOMED_CT_SYSTEM`, `LOINC_SYSTEM`, `CIE_10_SYSTEM` (URIs FHIR)
- Actualizado `__init__.py` — re-exports de todos los tipos nuevos + excepciones
- Creado `tests/test_query_builder.py` — 96 tests en 13 clases:
  - FHIRResourceType (7), TokenParam (6), DateParam (10), ReferenceParam (2), QuantityParam (4), StringParam (3), IncludeParam (3), SortParam (3), FHIRQueryBuilder (21), FHIRQueryToParams (6), ChainedParams (3), Golden (7), ExceptionHierarchy (2)
- Verificación: 131 tests verdes, ruff limpio, format limpio
- Golden tests: diabetes+edad, laboratorio glucosa, pacientes Buenos Aires, medicaciones activas, CIE-10, revinclude, observaciones con quantity

---

## [Sprint 2, Sesión 2.1] — 2026-03-03

### Terminology Resolver (SNOMED CT AR, CIE-10, LOINC)
- Extendida jerarquía de excepciones: `TerminologyError`, `TerminologyCodeNotFoundError`, `TerminologyDataError`
- Creado `saludai_core/terminology.py` (~490 líneas) — módulo principal:
  - `TerminologySystem` (StrEnum con URIs FHIR), `MatchType`
  - `TerminologyConcept` (frozen dataclass), `TerminologyMatch` (con `is_confident`, `needs_review`)
  - `TerminologyConfig` — thresholds, cache size configurables
  - `TerminologyResolver` — `resolve()`, `search()`, `lookup()`, LRU cache
  - Estrategia de fallback: exact display (ES/EN) → exact alias → fuzzy (token_sort_ratio + partial_ratio)
- Creado `saludai_core/data/snomed_ar.csv` — 96 códigos SNOMED CT (metabólicas, cardiovasculares, respiratorias, infecciosas LATAM, pediátricas, salud mental, oncología)
- Creado `saludai_core/data/cie10_ar.csv` — 45 códigos CIE-10
- Creado `saludai_core/data/loinc.csv` — 30 códigos LOINC (laboratorio)
- Agregada dependencia `rapidfuzz>=3` a saludai-core
- Actualizado `__init__.py` — re-exports de todos los tipos nuevos de terminology
- Creado `tests/test_terminology.py` — 35 tests unitarios:
  - Data loading (5), exact match (8), fuzzy match (8), no match (3), search (3), lookup (2), cache (3), config (2), golden (1)
- Verificación: 44 tests verdes, ruff limpio, format limpio
- Golden test: `"diabetes tipo 2"` → SNOMED `44054006` con `is_confident=True`

---

## [Sprint 1, Sesión 1.5] — 2026-03-03

### README, LICENSE, CONTRIBUTING.md
- Creado `LICENSE` — Apache 2.0 full text, Copyright 2026 SaludAI Labs
- Reescrito `README.md` (~70 líneas) — badges CI + License, visión, current status, quick start, project structure, contributing link
- Creado `CONTRIBUTING.md` (~95 líneas) — prerequisites, dev setup, code style (Ruff, type hints, Google docstrings), commit conventions, testing (pytest + integration), PR process, architecture links, code of conduct placeholder
- Actualizado `docs/ROADMAP.md` — sesión 1.5 marcada ✅, DoD Sprint 1 100% completado
- Sprint 1 (Fundación) completado — todas las 5 sesiones finalizadas

---

## [Sprint 1, Sesión 1.4] — 2026-03-03

### saludai-core: FHIR Client (connect, search, read)
- Creado `saludai_core/exceptions.py` — jerarquía de excepciones (SaludAIError → FHIRError → 4 subtipos)
- Creado `saludai_core/config.py` — FHIRConfig con pydantic-settings (env prefix SALUDAI_)
- Creado `saludai_core/fhir_client.py` — FHIRClient async con httpx
  - `check_connection()` → GET /metadata, valida FHIR R4
  - `read(type, id)` → GET /{type}/{id}, parsea con fhir.resources
  - `search(type, params)` → GET /{type}?params, retorna Bundle
  - Context manager (async with), auth bearer configurable, structlog logging
- Actualizado `__init__.py` — re-exports de FHIRClient, FHIRConfig, excepciones
- Creado `test_config.py` — 3 tests unitarios (defaults, env vars, explicit values)
- Creado `test_exceptions.py` — 5 tests unitarios (jerarquía, mensajes, catch)
- Creado `test_fhir_client.py` — 9 tests de integración contra HAPI FHIR
  - Marcados con `@pytest.mark.integration`, skip automático si HAPI no corre
  - check_connection, search patients, search by state, search by code, _count, read, read 404, empty results, connection error
- Registrado marker `integration` en pyproject.toml
- Verificado: 18 tests pasan (9 unitarios + 9 integración), ruff limpio
- Descubrimiento: fhir.resources v8+ usa `get_resource_type()` no `resource_type`
- Descubrimiento: HAPI no siempre retorna `total` en searchset bundles
- Creado `docs/knowledge/fhir-resources-python.md` — API, parsing, gotchas
- Actualizado `docs/knowledge/README.md` — nuevo entry
- Actualizado `docs/ROADMAP.md` — sesiones 1.1-1.4 marcadas ✅, DoD checkmarks
- Descubrimiento: HAPI no siempre retorna `total` en searchset bundles

---

## [Sprint 1, Sesión 1.3] — 2026-03-03

### Docker Compose (HAPI FHIR R4) + Knowledge Base
- Creado `docs/knowledge/` — knowledge base con investigación técnica
  - `hapi-fhir-docker.md` — imagen Docker, healthcheck, seeding, tips
  - `langfuse-setup.md` — Cloud vs self-hosted, env vars, integración
- Creado `data/seed/generate_seed_data.py` — generador de datos sintéticos argentinos
  - 55 pacientes: nombres argentinos, DNI, provincias ponderadas por población
  - 80 condiciones: SNOMED CT reales (diabetes, hipertensión, Chagas, dengue, etc.)
  - Reproducible (random.seed(42)), stdlib-only (sin dependencias externas)
- Generado `data/seed/seed_bundle.json` — bundle transaccional FHIR (124KB, 135 entries)
- Creado `data/seed/seed.sh` — script de seeding con polling + verificación
- Creado `data/seed/Dockerfile` — Alpine 3.20 + curl para seed sidecar
- Creado `docker-compose.yml` — HAPI FHIR R4 + seed sidecar
- Creado `.gitattributes` — LF line endings para .sh
- Creado `docs/decisions/006-langfuse-cloud.md` — ADR: Langfuse Cloud free tier
- Actualizado `.env.example` — Langfuse host → `https://cloud.langfuse.com`
- Actualizado `docs/ARCHITECTURE.md` — sección 5.1, diagrama infra, tabla ADRs
- Verificado: docker compose up → 55 pacientes + 80 condiciones, curl endpoints OK
- Descubrimiento: imagen HAPI es distroless (sin shell/curl) → polling desde sidecar

---

## [Sprint 1, Sesión 1.2] — 2026-03-03

### GitHub Actions CI + Pre-commit hooks
- Creado smoke tests en los 4 paquetes (`test_init.py` — importa y verifica `__version__`)
- Creado `.github/workflows/ci.yml` — CI completo con ruff check, ruff format, pytest
- Creado `.pre-commit-config.yaml` — ruff check --fix + ruff format via `ruff-pre-commit`
- Agregado `pre-commit>=4` a dev dependencies
- Fix: `addopts = "--import-mode=importlib"` en pytest config para monorepo
- Verificado: 4 tests pasan, ruff limpio, pre-commit limpio

---

## [Sprint 1, Sesión 1.1] — 2026-03-03

### Monorepo UV + Estructura de paquetes
- Configurado git remote origin → github.com/saludai-labs/saludai
- Creado `pyproject.toml` raíz con UV workspace (4 paquetes)
- Creado `packages/saludai-core/` — FHIR client, terminología, tipos compartidos
- Creado `packages/saludai-agent/` — Agent loop con tools
- Creado `packages/saludai-mcp/` — MCP server para Claude Desktop
- Creado `packages/saludai-api/` — FastAPI REST interface
- Configuradas dependencias inter-paquete via `tool.uv.sources`
- Creado `.env.example` con todas las variables de entorno
- Creado `README.md` mínimo
- Verificado: `uv sync --all-packages` instala 77 paquetes correctamente
- Verificado: `ruff check .` pasa limpio
- Dev dependencies: ruff, pytest, pytest-asyncio, pytest-cov, mypy

---

## [Pre-Sprint] — 2026-03-03

### Documentación inicial
- Creado CLAUDE.md con instrucciones para Claude Code
- Creado ROADMAP.md con 4 sprints detallados (20 sesiones)
- Creado ARCHITECTURE.md con evaluación de stack y patrones
- Creado template de ADR para decisiones arquitectónicas
- Creado PROGRESS.md para tracking de estado
- Creado estructura de tasks/ (todo, backlog, lessons)
