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
