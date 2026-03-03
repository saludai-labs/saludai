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
