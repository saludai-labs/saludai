# SaludAI — Changelog

Registro de cambios por sesión de desarrollo.

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
