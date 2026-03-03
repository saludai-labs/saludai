# SaludAI — Estado Actual

**Última actualización:** 2026-03-03
**Sprint actual:** Sprint 1 — Fundación
**Sesión actual:** 1.2 — GitHub Actions CI + pre-commit hooks

---

## Estado General

🟢 **Sprint 1 en progreso** — Monorepo configurado, CI pipeline configurado, pre-commit hooks activos.

## Última Sesión Completada

**Sprint 1, Sesión 1.2** — GitHub Actions CI + pre-commit hooks

### Lo que se hizo
- Smoke tests en los 4 paquetes (`test_init.py` que importa y verifica `__version__`)
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
  - Trigger: push/PR a `main`
  - Steps: checkout → setup-uv → python 3.12 → sync → ruff check → ruff format --check → pytest
  - Concurrency: cancela runs previos en el mismo ref
- Pre-commit hooks (`.pre-commit-config.yaml`)
  - `ruff check --fix` (lint con autofix)
  - `ruff format` (formateo)
  - Usa `ruff-pre-commit` oficial de Astral
- `pre-commit>=4` agregado a `dependency-groups.dev`
- Fix: `addopts = "--import-mode=importlib"` en pytest config para resolver conflicto de módulos homónimos en monorepo

### Verificación
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → 12 files already formatted
- `uv run pytest --tb=short` → 4 passed in 0.03s
- `uv run pre-commit run --all-files` → ruff Passed, ruff-format Passed

### Detalles técnicos
- Pre-commit usa `ruff-pre-commit` v0.9.10 (independiente del ruff en dev deps)
- pytest `--import-mode=importlib` necesario porque múltiples `tests/test_init.py` colisionan con import mode clásico
- CI usa `astral-sh/setup-uv@v5` con cache habilitado
- Python 3.12 en CI (single version, sin matrix por ahora)

## Próxima Sesión

**Sprint:** 1 — Fundación
**Sesión:** 1.3 — Docker Compose (HAPI FHIR + Langfuse)
**Objetivo:** `docker compose up` levanta HAPI FHIR R4 + Langfuse funcional
**Referencia:** `docs/ROADMAP.md` → Sprint 1 → Sesión 1.3

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

## Decisiones Pendientes

- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
- [ ] ¿Langfuse Cloud (free tier) o self-hosted desde el día 1?
