# SaludAI — Estado Actual

**Última actualización:** 2026-03-03
**Sprint actual:** Pre-Sprint (Setup)
**Sesión actual:** —

---

## Estado General

🟡 **Pre-desarrollo** — Documentación de arquitectura y planificación completadas. Pendiente inicio de Sprint 1.

## Próxima Sesión

**Sprint:** 1 — Fundación
**Sesión:** 1.1 — Crear GitHub Org, repos, monorepo UV
**Objetivo:** Repos creados, `uv sync` funcional, estructura de paquetes lista
**Referencia:** `docs/ROADMAP.md` → Sprint 1 → Sesión 1.1

## Lo que está listo

- [x] CLAUDE.md con instrucciones completas para Claude Code
- [x] ROADMAP.md con sprints y sesiones detalladas
- [x] ARCHITECTURE.md con decisiones técnicas y evaluación de stack
- [x] Template de ADR para decisiones futuras
- [x] Plan de Etapa 1 documentado

## Lo que falta para arrancar (Sesión 1.1)

- [ ] Crear GitHub Org `saludai-labs`
- [ ] Crear repo `saludai` (público)
- [ ] Crear repo `saludai-data-ar` (público)
- [ ] Crear repo `saludai-private` (privado, vacío)
- [ ] Push de estos archivos al repo
- [ ] Setup pyproject.toml raíz con UV workspace
- [ ] Crear estructura de paquetes vacía

## Blockers

Ninguno.

## Decisiones pendientes

- [ ] Nombre exacto de la GitHub Org (¿`saludai-labs`? ¿`saludai-health`? ¿`saludai-fhir`?)
- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
- [ ] ¿Langfuse Cloud (free tier) o self-hosted desde el día 1?
