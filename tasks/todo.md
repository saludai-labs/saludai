# SaludAI — TODO (Sesion actual)

> Actualizar al inicio de cada sesion con las tareas concretas.
> Marcar como completadas durante la sesion.

## Sesion: Sprint 4, Sesion 4.3 — PyPI packaging + Docker image

### Meta-paquete `saludai`
- [x] Convertir root pyproject.toml en meta-paquete que depende de core + agent + mcp
- [x] Agregar entry point `saludai` CLI (`saludai mcp`, `saludai version`)
- [x] Crear `src/saludai/__init__.py` + `src/saludai/cli.py`

### Metadata PyPI (todos los paquetes)
- [x] Agregar classifiers, URLs, keywords a cada pyproject.toml

### Build verification
- [x] `uv build` cada paquete — 8 artifacts generados
- [x] Wheels incluyen CSVs y locale data

### Dockerfile
- [x] Crear Dockerfile con UV, entrypoint `saludai mcp`
- [x] `.dockerignore`

### CI: publish workflow
- [x] `.github/workflows/publish.yml` — PyPI trusted publishers + GHCR Docker

### Decision
- [x] REST API (4.2) movida a backlog

### Documentacion
- [x] Protocolo fin de sesion
