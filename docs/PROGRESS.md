# SaludAI — Estado Actual

**Última actualización:** 2026-03-03
**Sprint actual:** Sprint 1 — Fundación
**Sesión actual:** 1.5 — README, LICENSE, CONTRIBUTING.md

---

## Estado General

🟢 **Sprint 1 completo** — Monorepo configurado, CI activo, Docker Compose con HAPI FHIR R4, FHIR client funcional, repo presentable para público.

## Última Sesión Completada

**Sprint 1, Sesión 1.5** — README, LICENSE (Apache 2.0), CONTRIBUTING.md

### Lo que se hizo
- `LICENSE` — Apache 2.0 full text, Copyright 2026 SaludAI Labs
- `README.md` — reescrito (~70 líneas): badges CI + License, visión, current status, quick start, project structure, contributing link
- `CONTRIBUTING.md` — creado (~95 líneas): prerequisites, dev setup, code style, commit conventions, testing, PR process, architecture links, code of conduct placeholder
- Verificación: ruff check limpio, 9/9 unit tests pasan
- Actualizado ROADMAP.md — sesión 1.5 marcada ✅, DoD 100% completado

### Verificación
- `uv run ruff check .` → All checks passed
- `uv run pytest packages/saludai-core/` → 9 passed (unit), 9 integration (con HAPI)
- `LICENSE` existe con texto Apache 2.0 completo
- `README.md` tiene badges, quick start, y estructura
- `CONTRIBUTING.md` tiene setup, code style, commit conventions

## Sprint 1 — Completado

Todas las sesiones del Sprint 1 están finalizadas:
- ✅ 1.1 — Monorepo UV + estructura de paquetes
- ✅ 1.2 — GitHub Actions CI + pre-commit hooks
- ✅ 1.3 — Docker Compose: HAPI FHIR R4 + datos sintéticos argentinos
- ✅ 1.4 — saludai-core: FHIR client (connect, search, read)
- ✅ 1.5 — README, LICENSE, CONTRIBUTING.md

## Próxima Sesión

**Sprint:** 2 — El Cerebro del Agente
**Sesión:** 2.1 — Terminology Resolver (SNOMED CT AR, CIE-10, LOINC)
**Objetivo:** "diabetes tipo 2" → SNOMED 44054006 con tests
**Referencia:** `docs/ROADMAP.md` → Sprint 2 → Sesión 2.1

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

## Decisiones Pendientes

- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
