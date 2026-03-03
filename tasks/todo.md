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
