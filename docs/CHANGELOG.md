# SaludAI — Changelog

Registro de cambios por sesión de desarrollo.

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
