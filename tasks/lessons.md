# SaludAI — Lecciones Aprendidas

> Actualizar después de CADA corrección del usuario.
> Claude Code debe leer este archivo al inicio de cada sesión.
> Formato: fecha + patrón + regla para evitarlo.

---

## Reglas activas

### 2026-03-03: No agregar Co-Authored-By en commits
**Qué pasó:** Agregué `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` al primer commit.
**Por qué estuvo mal:** El usuario no quiere que Claude se agregue como coautor.
**Regla:** Nunca incluir `Co-Authored-By` en los mensajes de commit.

### 2026-03-03: UV workspace — root no necesita build-system
**Qué pasó:** Puse `[build-system]` en el `pyproject.toml` raíz y hatchling falló porque no encontró un paquete `saludai/` para buildear.
**Por qué estuvo mal:** El root de un UV workspace es un proyecto virtual — coordina paquetes pero no se buildea como wheel.
**Regla:** En UV workspaces, el pyproject.toml raíz NO debe tener `[build-system]`. Solo los sub-paquetes lo necesitan.

### 2026-03-03: UV workspace — dependencias entre paquetes necesitan tool.uv.sources
**Qué pasó:** `uv sync` falló porque `saludai-agent` depende de `saludai-core` pero no tenía `tool.uv.sources`.
**Por qué estuvo mal:** UV necesita saber explícitamente que una dependencia se resuelve desde el workspace local.
**Regla:** Si un paquete del workspace depende de otro, agregar `[tool.uv.sources]\npackage-name = { workspace = true }` en su pyproject.toml.

### 2026-03-03: UV — usar dependency-groups.dev en vez de tool.uv.dev-dependencies
**Qué pasó:** Usé `[tool.uv] dev-dependencies` que está deprecado.
**Regla:** Usar `[dependency-groups] dev = [...]` en el pyproject.toml raíz para dev-dependencies.

### 2026-03-03: Hatchling requiere que los archivos declarados existan
**Qué pasó:** Declaré `readme = "README.md"` en pyproject.toml pero el archivo no existía, y hatchling falló.
**Regla:** No declarar `readme` en pyproject.toml hasta que el archivo exista, o crear el archivo primero.

<!-- Ejemplo de formato:
### 2026-03-05: No usar requests, usar httpx
**Qué pasó:** Usé `requests` para el FHIR client.
**Por qué estuvo mal:** El proyecto usa httpx (async-first). requests bloquea el event loop.
**Regla:** Siempre usar `httpx.AsyncClient` para HTTP. Never import requests.
-->
