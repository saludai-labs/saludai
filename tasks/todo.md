# SaludAI — TODO (Sesión actual)

> Actualizar al inicio de cada sesión con las tareas concretas.
> Marcar como completadas durante la sesión.

## Sesión: Pre-Sprint

- [x] Crear CLAUDE.md
- [x] Crear ROADMAP.md
- [x] Crear ARCHITECTURE.md
- [x] Crear ADR template + primeros ADRs
- [x] Crear PROGRESS.md, CHANGELOG.md
- [x] Crear estructura de tasks/

## Sesión: Sprint 1, Sesión 1.1

- [x] Crear GitHub Org `saludai-labs` (hecho por el usuario)
- [x] Crear repos en GitHub (hecho por el usuario)
- [x] Configurar git remote origin
- [x] pyproject.toml raíz con UV workspace config
- [x] Estructura de paquetes vacía con __init__.py (core, agent, mcp, api)
- [x] .env.example con todas las variables
- [x] README.md mínimo
- [x] `uv sync --all-packages` funciona correctamente
- [x] `ruff check .` pasa limpio
- [ ] Push inicial al repo

## Sesión: Sprint 1, Sesión 1.2

- [x] Smoke tests en cada paquete (test_init.py que importa y verifica __version__)
- [x] GitHub Actions CI (.github/workflows/ci.yml — ruff check, ruff format, pytest)
- [x] Pre-commit hooks (.pre-commit-config.yaml — ruff check --fix, ruff format)
- [x] Agregar `pre-commit` a dev dependencies
- [x] Verificación: ruff check, ruff format --check, pytest, pre-commit run --all-files
- [x] Actualizar PROGRESS.md, CHANGELOG.md

## Sesión: Sprint 1, Sesión 1.3

- [x] Knowledge base: `docs/knowledge/` (README, HAPI FHIR, Langfuse)
- [x] Seed data generator: `data/seed/generate_seed_data.py` (55 pacientes AR, ~80 condiciones)
- [x] Generar `data/seed/seed_bundle.json` (bundle transaccional pre-generado)
- [x] Seed infrastructure: `data/seed/seed.sh` + `data/seed/Dockerfile` (Alpine + curl)
- [x] `docker-compose.yml` (HAPI FHIR R4 + seed sidecar)
- [x] `.gitattributes` (LF endings para .sh)
- [x] `.env.example` actualizado (Langfuse → Cloud)
- [x] ADR-006: Langfuse Cloud (free tier)
- [x] `docs/ARCHITECTURE.md` actualizado (sección 5.1 Docker Compose)
- [x] Verificación: docker compose up → seed completo → curl endpoints → datos argentinos
- [x] Verificación: ruff check limpio, pytest 4/4 pasan
- [x] Actualizar PROGRESS.md, CHANGELOG.md

## Sesión: Sprint 1, Sesión 1.4

- [x] `saludai_core/exceptions.py` — jerarquía SaludAIError → FHIRError → 4 subtipos
- [x] `saludai_core/config.py` — FHIRConfig con pydantic-settings (env prefix SALUDAI_)
- [x] `saludai_core/fhir_client.py` — FHIRClient async (check_connection, read, search)
- [x] `__init__.py` — re-exports de FHIRClient, FHIRConfig, excepciones
- [x] `tests/test_config.py` — 3 tests unitarios
- [x] `tests/test_exceptions.py` — 5 tests unitarios
- [x] `tests/test_fhir_client.py` — 9 tests de integración (@pytest.mark.integration)
- [x] Registrar marker `integration` en pyproject.toml
- [x] Verificación: ruff check limpio, 18/18 tests pasan
- [x] Actualizar PROGRESS.md, CHANGELOG.md, lessons.md

## Sesión: Sprint 1, Sesión 1.5

- [x] Crear `LICENSE` — Apache 2.0 full text, Copyright 2026 SaludAI Labs
- [x] Reescribir `README.md` — badges CI + License, vision, quick start, structure, contributing link
- [x] Crear `CONTRIBUTING.md` — prerequisites, dev setup, code style, commits, testing, PR process
- [x] Verificación: ruff check limpio, 9/9 unit tests pasan
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md

## Sesión: Sprint 2, Sesión 2.1

- [x] Extender jerarquía de excepciones (TerminologyError, TerminologyCodeNotFoundError, TerminologyDataError)
- [x] Agregar dependencia `rapidfuzz>=3` a saludai-core + `uv sync`
- [x] Crear `saludai_core/data/snomed_ar.csv` (~96 códigos SNOMED CT AR)
- [x] Crear `saludai_core/data/cie10_ar.csv` (~45 códigos CIE-10)
- [x] Crear `saludai_core/data/loinc.csv` (~30 códigos LOINC)
- [x] Implementar `saludai_core/terminology.py` (TerminologyResolver, enums, modelos)
- [x] Actualizar `__init__.py` con re-exports de tipos nuevos
- [x] Crear `tests/test_terminology.py` (35 tests unitarios)
- [x] Verificación: 44 tests verdes, ruff check limpio, ruff format limpio
- [x] Actualizar PROGRESS.md, CHANGELOG.md, todo.md, ROADMAP.md

## Sesión: Sprint 2, Sesión 2.2

- [x] Agregar `QueryBuilderError`, `QueryBuilderValidationError` a `exceptions.py`
- [x] Implementar `saludai_core/query_builder.py` (enums, dataclasses, factories, builder)
- [x] Actualizar `__init__.py` con re-exports de tipos nuevos
- [x] Crear `tests/test_query_builder.py` (96 tests en 13 clases)
- [x] Verificación: 131 tests verdes, ruff check limpio, ruff format limpio
- [x] Actualizar PROGRESS.md, CHANGELOG.md, todo.md, ROADMAP.md

## Sesión: Sprint 2, Sesión 2.3

- [x] Crear `saludai_agent/exceptions.py` — AgentError, AgentLoopError, ToolExecutionError, LLMError, LLMResponseError
- [x] Crear `saludai_agent/config.py` — AgentConfig con pydantic-settings
- [x] Crear `saludai_agent/types.py` — Message, ToolCall, ToolResult, TokenUsage, LLMResponse, AgentResult
- [x] Crear `saludai_agent/prompts.py` — SYSTEM_PROMPT + PROMPT_VERSION
- [x] Crear `saludai_agent/llm.py` — LLMClient Protocol + Anthropic + OpenAI clients + factory
- [x] Crear `saludai_agent/tools.py` — ToolRegistry + resolve_terminology + search_fhir + format_bundle_summary
- [x] Crear `saludai_agent/loop.py` — AgentLoop class
- [x] Actualizar `__init__.py` + `pyproject.toml`
- [x] Crear tests: test_exceptions, test_config, test_types, test_prompts, test_llm, test_tools, test_loop
- [x] Verificación: 126 agent tests + 131 core tests, ruff check limpio, ruff format limpio
- [x] Actualizar PROGRESS.md, CHANGELOG.md, todo.md, ROADMAP.md

## Sesión: Sprint 2, Sesión 2.4

- [x] Agregar `langfuse_enabled: bool = False` a `AgentConfig`
- [x] Agregar `trace_id`, `trace_url` a `AgentResult`
- [x] Crear `saludai_agent/tracing.py` — Tracer protocol, LangfuseTracer, NoOpTracer, create_tracer
- [x] Instrumentar `AgentLoop.run()` — start_trace, log_generation, log_tool_call, end_trace
- [x] Actualizar `__init__.py` con exports de tracing
- [x] Actualizar `scripts/demo_agent.py` con tracer
- [x] Crear `tests/test_tracing.py` (22 tests) + 4 tests tracing en test_loop.py
- [x] Verificación: 155 agent tests + 150 core tests = 305 total, ruff limpio, format limpio
- [x] Actualizar PROGRESS.md, CHANGELOG.md, todo.md, ROADMAP.md

## Sesión: Sprint 2, Sesión 2.5

- [x] Crear benchmarks/ scaffold (config.py, __init__.py)
- [x] Crear benchmarks/dataset.py + dataset.json (25 preguntas curadas)
- [x] Crear benchmarks/judge.py (LLM-as-judge, evaluación binaria)
- [x] Crear benchmarks/metrics.py (BenchmarkMetrics, compute_metrics)
- [x] Crear benchmarks/results.py (QuestionResult, write_results_json, print_summary)
- [x] Crear benchmarks/harness.py (EvalHarness: agent + judge)
- [x] Crear benchmarks/run_eval.py (CLI entry point)
- [x] Crear benchmarks/__main__.py (python -m benchmarks support)
- [x] Crear tests: test_dataset (9), test_judge (8), test_metrics (9), test_results (4) = 30 tests
- [x] Actualizar pyproject.toml (testpaths, known-first-party)
- [x] Actualizar .gitignore (benchmarks/results/)
- [x] Verificación: 30 benchmark tests + 307 package tests = 337 total, ruff limpio
- [x] Ejecutar benchmark real: 88% accuracy (22/25)
- [x] Actualizar README.md con tabla de scores
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md, todo.md

## Sesión: Sprint 2, Sesión 2.6

- [x] Crear `docs/experiments/EXPERIMENTS.md` — documento formal de experimentos (Exp 0-4)
- [x] Agregar 2 LOINC codes a `loinc.csv` (PA sistólica, PA diastólica)
- [x] Enriquecer `generate_seed_data.py` con Observations, MedicationRequests, Encounters
- [x] Regenerar `seed_bundle.json` (536 entries) + actualizar `seed.sh`
- [x] Verificar Docker seed con nuevos resource types
- [x] Expandir `dataset.json` de 25 a 50 preguntas + endurecer criterios
- [x] Actualizar `test_dataset.py` (50 preguntas)
- [x] Fix `fhir_client.py` — search() retorna raw dict (fix MedicationRequest parsing)
- [x] Fix `tools.py` — format_bundle_summary() para dicts
- [x] Judge híbrido: pre-check programático para rangos numéricos + markdown fence fix
- [x] 8 tests nuevos para judge range check
- [x] Ejecutar benchmark completo: **60.0% accuracy** (30/50)
- [x] Actualizar README.md, EXPERIMENTS.md con resultados
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md, todo.md

## Sesión: Sprint 3, Sesión 3.1

- [x] Agregar `SummaryMode` enum y `.summary()` method a `FHIRQueryBuilder`
- [x] Actualizar `__init__.py` con re-export de `SummaryMode`
- [x] `execute_search_fhir()` — inyectar `_count=200` por defecto
- [x] `format_bundle_summary()` — manejar bundles `_summary=count`
- [x] Actualizar `SEARCH_FHIR_DEFINITION` params description
- [x] Actualizar `SYSTEM_PROMPT` con estrategia de consulta, bump version a v1.1
- [x] Tests nuevos en test_tools.py y test_query_builder.py
- [x] Fix test_prompts.py (version assertion v1.1)
- [x] `uv run pytest` → 355 passed
- [x] `uv run ruff check .` → All checks passed
- [x] Benchmark: 82.0% accuracy (41/50) — +22pp vs Exp 1
- [x] Documentar Exp 2 en EXPERIMENTS.md
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md, todo.md

## Sesión: Sprint 3, Sesión 3.2

- [x] Fix `snomed_ar.csv` — display de `38341003` → "Hipertensión arterial sistémica"
- [x] Agregar `read_raw()` a `FHIRClient`
- [x] Agregar `get_resource` tool (definition + executor + registry)
- [x] Subir `agent_max_iterations` de 5 a 8 (config + .env)
- [x] Actualizar system prompt a v1.2 (get_resource, _include, medicamentos)
- [x] Tests nuevos/actualizados (12 tests)
- [x] `uv run pytest` → 365 passed
- [x] `uv run ruff check .` → All checks passed
- [x] Benchmark: 86.0% accuracy (43/50, 0 errors) — +4pp vs Exp 2
- [x] Documentar Exp 3 en EXPERIMENTS.md
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md, todo.md

## Sesión: Sprint 3, Sesión 3.3

- [x] Agregar `EXECUTE_CODE_DEFINITION` a tools.py
- [x] Implementar `execute_code()` con sandbox (builtins, imports, timeout)
- [x] Registrar `execute_code` en `ToolRegistry`
- [x] Actualizar system prompt a v1.3 (tool #4, sección "Procesamiento de datos")
- [x] Tests nuevos (~26 tests: definition, executor, safety, edge cases, registry, prompts)
- [x] `uv run ruff check .` → All checks passed
- [x] `uv run ruff format .` → limpio
- [x] `uv run pytest` → 391 passed
- [x] Benchmark: 94.0% accuracy (47/50, 1 error) — +8pp vs Exp 3
- [x] Documentar Exp 4 en EXPERIMENTS.md
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md, todo.md

## Sesión: Sprint 3, Sesión 3.4a — Limpieza de Deuda Técnica

- [x] Crear ADR-002: No LangChain — Custom Agent Loop
- [x] Crear ADR-004: Langfuse para Observabilidad
- [x] Crear ADR-005: FHIR R4 Only
- [x] Configurar pytest-cov en pyproject.toml (source, fail_under=70, addopts)
- [x] Agregar coverage al CI (.github/workflows/ci.yml)
- [x] Correr coverage y evaluar → 84.57% (supera 70%)
- [x] Actualizar PROGRESS.md, CHANGELOG.md, todo.md, backlog.md

## Sesión: Sprint 3, Sesión 3.4b — Sistema de Locale Packs

- [x] Crear `saludai_core/locales/_types.py` — LocalePack + TerminologySystemDef
- [x] Crear `saludai_core/locales/__init__.py` — load_locale_pack() factory
- [x] Agregar `LocaleNotFoundError` a exceptions.py
- [x] Crear AR locale pack (ar/__init__.py, _pack.py, _prompt.py)
- [x] Copiar CSVs de data/ a locales/ar/
- [x] Refactorizar TerminologyResolver — aceptar locale_pack param
- [x] Actualizar saludai_core/__init__.py — re-exports de locale types
- [x] Agregar `locale: str = "ar"` a AgentConfig
- [x] ToolRegistry — aceptar locale_pack, usar para descriptions y enum
- [x] AgentLoop — aceptar locale_pack, usar system_prompt del pack
- [x] prompts.py — backward-compat alias desde AR pack
- [x] Tests nuevos: test_locale_pack.py (core), test_locale_integration.py (agent)
- [x] ADR-007: docs/decisions/007-locale-packs.md
- [x] docs/LOCALE_GUIDE.md — guía para crear locale packs
- [x] ARCHITECTURE.md — sección 5b locale packs
- [x] README.md — sección locale packs
- [x] `uv run pytest` → 375 passed
- [x] `uv run ruff check .` → All checks passed
- [x] Actualizar PROGRESS.md, CHANGELOG.md, ROADMAP.md, todo.md
