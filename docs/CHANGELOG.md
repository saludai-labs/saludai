# SaludAI — Changelog

Registro de cambios por sesión de desarrollo.

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
