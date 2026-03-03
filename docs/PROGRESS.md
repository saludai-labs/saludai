# SaludAI — Estado Actual

**Última actualización:** 2026-03-03
**Sprint actual:** Sprint 1 — Fundación
**Sesión actual:** 1.1 — Monorepo UV + estructura de paquetes

---

## Estado General

🟢 **Sprint 1 en progreso** — Monorepo configurado, workspace UV funcional, estructura de paquetes lista.

## Última Sesión Completada

**Sprint 1, Sesión 1.1** — Monorepo UV + estructura de paquetes

### Lo que se hizo
- GitHub Org `saludai-labs` creada (por el usuario)
- Repos creados en GitHub (por el usuario)
- Git remote configurado (`origin` → `https://github.com/saludai-labs/saludai.git`)
- `pyproject.toml` raíz con UV workspace (4 miembros)
- 4 paquetes creados: `saludai-core`, `saludai-agent`, `saludai-mcp`, `saludai-api`
- Cada paquete con `pyproject.toml`, `src/`, `tests/`
- Dependencias inter-paquete configuradas con `tool.uv.sources`
- `.env.example` con todas las variables de entorno
- `README.md` mínimo
- `uv sync --all-packages` funcional
- `ruff check .` pasa limpio

### Detalles técnicos
- Python 3.14 detectado (compatible con >=3.12)
- UV 0.9.26
- Se usó `dependency-groups.dev` (no el deprecado `tool.uv.dev-dependencies`)
- Root pyproject.toml sin `[build-system]` (es workspace virtual, no paquete)
- Sub-paquetes sin `readme` en pyproject.toml (se agrega cuando se creen los READMEs)

## Próxima Sesión

**Sprint:** 1 — Fundación
**Sesión:** 1.2 — GitHub Actions CI + pre-commit hooks
**Objetivo:** CI verde en push, Ruff + Pytest en pipeline
**Referencia:** `docs/ROADMAP.md` → Sprint 1 → Sesión 1.2

## Blockers

Ninguno.

## Decisiones Tomadas

- GitHub Org: `saludai-labs` (confirmado)
- Git remote via HTTPS (no SSH)
- Root pyproject.toml es workspace virtual (sin build-system)
- `dependency-groups.dev` para dev-dependencies (estándar actual de UV)

## Decisiones Pendientes

- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
- [ ] ¿Langfuse Cloud (free tier) o self-hosted desde el día 1?
