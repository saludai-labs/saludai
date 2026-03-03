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

### 2026-03-03: Pytest en monorepo necesita --import-mode=importlib
**Qué pasó:** Pytest falló con "import file mismatch" al tener `tests/test_init.py` en múltiples paquetes.
**Por qué estuvo mal:** El import mode clásico de pytest usa `sys.path` y `__init__.py`, lo que causa colisiones cuando múltiples paquetes tienen test files con el mismo nombre.
**Regla:** En monorepos UV con múltiples paquetes, siempre configurar `addopts = "--import-mode=importlib"` en `[tool.pytest.ini_options]`.

### 2026-03-03: HAPI FHIR Docker image es distroless — no tiene shell ni curl
**Qué pasó:** Configuré Docker healthcheck con `CMD curl` y luego `CMD-SHELL wget`, ambos fallaron porque la imagen `hapiproject/hapi:latest` es distroless (sin shell, sin utilidades).
**Por qué estuvo mal:** Asumí que la imagen HAPI incluía curl o al menos wget/sh. Es una imagen JVM pura.
**Regla:** Para HAPI FHIR, hacer polling desde un sidecar container (Alpine + curl) en vez de Docker healthcheck nativo. No usar `depends_on: condition: service_healthy` con imágenes distroless.

### 2026-03-03: HAPI FHIR JSON format — "total" tiene espacio antes del valor
**Qué pasó:** El grep `'"total":[0-9]*'` no matcheaba porque HAPI formatea como `"total": 55` (con espacio).
**Regla:** En scripts que parsean JSON de HAPI, usar grep patterns con espacios opcionales: `'"total" *: *[0-9]*'`.

### 2026-03-03: fhir.resources v8+ usa get_resource_type() no resource_type
**Qué pasó:** En tests usé `patient.resource_type` y falló con `AttributeError`.
**Por qué estuvo mal:** `fhir.resources` v8+ (Pydantic v2) expone el resource type como método `get_resource_type()`, no como atributo `resource_type` ni `resourceType`.
**Regla:** Siempre usar `.get_resource_type()` para obtener el tipo de recurso FHIR. Usar `.model_validate()` para parsear, `.model_dump()` para serializar.

### 2026-03-03: HAPI FHIR no siempre retorna total en búsquedas
**Qué pasó:** El test `address-state` falló porque `bundle.total` era `None`.
**Por qué estuvo mal:** FHIR spec no obliga a incluir `total` en searchset bundles. HAPI lo omite en algunas búsquedas.
**Regla:** En tests de búsqueda FHIR, verificar `bundle.entry` (no None y len >= 1) en vez de confiar en `bundle.total`.

<!-- Ejemplo de formato:
### 2026-03-05: No usar requests, usar httpx
**Qué pasó:** Usé `requests` para el FHIR client.
**Por qué estuvo mal:** El proyecto usa httpx (async-first). requests bloquea el event loop.
**Regla:** Siempre usar `httpx.AsyncClient` para HTTP. Never import requests.
-->
