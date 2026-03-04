# SaludAI — Lecciones Aprendidas

> Actualizar después de CADA corrección del usuario.
> Claude Code debe leer este archivo al inicio de cada sesión.
> Formato: fecha + patrón + regla para evitarlo.

---

## Reglas activas

### 2026-03-03: rapidfuzz scores son 0-100, no 0-1
**Qué pasó:** Definí `EXACT_MATCH_SCORE = 1.0` pero rapidfuzz retorna scores en rango 0-100. Los tests de `is_confident` fallaron porque 1.0 < 70.0 (threshold).
**Regla:** Mantener TODAS las scores en la escala 0-100 para consistencia con rapidfuzz. EXACT_MATCH_SCORE = 100.0.

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

### 2026-03-04: pydantic-settings con env_file lee TODAS las vars del .env
**Qué pasó:** Agregué `env_file=".env"` a AgentConfig y pydantic-settings rechazó todas las vars que no estaban en el modelo (FHIR, Langfuse, etc.) con "Extra inputs are not permitted".
**Por qué estuvo mal:** El `.env` es compartido entre paquetes. Cada config solo define un subconjunto.
**Regla:** Usar `extra="ignore"` en SettingsConfigDict cuando el .env tiene vars de múltiples paquetes. Preferir `load_dotenv()` en scripts de aplicación en vez de `env_file` en el modelo.

### 2026-03-04: MagicMock(name=...) no funciona como atributo — usa .name = después
**Qué pasó:** `MagicMock(name="resolve_terminology")` no setea `.name` como string porque `name` es un parámetro especial de Mock (el nombre del mock para debugging).
**Regla:** Para mocks donde `.name` debe ser un string real, crear el mock primero y luego asignar: `mock = MagicMock(); mock.name = "value"`.

### 2026-03-04: Windows console (cp1251) no soporta caracteres españoles
**Qué pasó:** `print(result.answer)` falló con UnicodeEncodeError porque la consola de Windows usa cp1251.
**Regla:** En scripts que imprimen texto en español, usar `sys.stdout.reconfigure(encoding="utf-8")` al inicio.

### 2026-03-04: Langfuse SDK v3 cambió toda la API — no tiene .trace()
**Qué pasó:** Implementé LangfuseTracer usando `langfuse.Langfuse().trace()` (API v2) pero langfuse v3.14+ eliminó ese método.
**Por qué estuvo mal:** No verifiqué la API actual del SDK instalado. La v3 usa `start_span()`, `start_generation()`, y context-based tracing.
**Regla:** Antes de integrar una librería, verificar la API real con `dir(obj)` o `help(method)`. No confiar en docs/ejemplos que pueden ser de versiones anteriores. Langfuse v3: `start_span()` (root), `.start_generation()` / `.start_span()` (children), `.end()` para cerrar.

### 2026-03-04: Usar Python 3.12, no 3.14 — langfuse incompatible
**Qué pasó:** El venv se creó con Python 3.14 (default del sistema) pero langfuse SDK usa pydantic v1 internamente, que no es compatible con 3.14.
**Regla:** Siempre crear el venv con `uv venv --python 3.12`. El proyecto especifica `>=3.12` pero 3.14 rompe dependencias. Verificar con `uv run python --version`.

### 2026-03-04: fhir.resources v8+ con Pydantic v2 extra="forbid" rompe choice-type fields
**Qué pasó:** `fhir.resources` parseo de MedicationRequest falló porque Pydantic v2 con `extra="forbid"` rechaza `medicationCodeableConcept` como campo extra (espera solo `medication`).
**Por qué estuvo mal:** FHIR R4 usa "choice types" donde un field como `medication[x]` se serializa como `medicationCodeableConcept` o `medicationReference`. La librería fhir.resources v8+ es demasiado estricta.
**Regla:** Para `FHIRClient.search()`, retornar el raw dict en vez de parsear con fhir.resources. Solo usar `model_validate()` para `read()` de recursos individuales donde el tipo es conocido y no tiene choice types problemáticos.

### 2026-03-04: Haiku no respeta instrucciones complejas de range-checking en judge prompts
**Qué pasó:** El judge prompt decía "si notes dice 'entre 13 y 17', aceptar cualquier número en ese rango". Haiku reconocía el rango en su razonamiento pero igual devolvía INCORRECT.
**Regla:** Para evaluación de rangos numéricos, usar pre-check programático (regex + comparación) en vez de confiar en que un LLM pequeño siga instrucciones de comparación numérica. Solo caer al LLM para evaluación semántica.

<!-- Ejemplo de formato:
### 2026-03-05: No usar requests, usar httpx
**Qué pasó:** Usé `requests` para el FHIR client.
**Por qué estuvo mal:** El proyecto usa httpx (async-first). requests bloquea el event loop.
**Regla:** Siempre usar `httpx.AsyncClient` para HTTP. Never import requests.
-->
