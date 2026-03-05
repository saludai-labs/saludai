# SaludAI — TODO (Sesion actual)

> Actualizar al inicio de cada sesion con las tareas concretas.
> Marcar como completadas durante la sesion.

## Sesion: Sprint 4, Sesion 4.9 — FHIR Awareness Level 2

### Deliverable B: AR Custom Search Params
- [x] Agregar `_CUSTOM_SEARCH_PARAMS` tuple con 4 params AR-especificos
- [x] Importar `CustomSearchParamDef` y pasar al constructor de `LocalePack`
- [x] Test: AR pack tiene custom_search_params no vacios
- [x] Test: prompt incluye "Parametros de busqueda custom"

### Deliverable A: Extension-Aware Resource Summarizer
- [x] `_extract_extension_value()` — extrae valor segun value_type
- [x] `_extract_extensions(resource, extension_defs)` — traduce URLs a name=value
- [x] Agregar `extension_defs` param a `_summarize_resource()`
- [x] Agregar `extension_defs` param a `format_bundle_summary()`
- [x] Agregar `extension_defs` param a `execute_search_fhir()` y `execute_get_resource()`
- [x] `ToolRegistry.__init__` almacena `_extension_defs` del locale pack
- [x] Wiring: registry pasa extension_defs a executors
- [x] Tests: string, boolean, code, CodeableConcept, Coding, Address
- [x] Tests: coding fallback to code, unknown URL skipped, no extensions, empty defs
- [x] Tests: integration con summarize_resource, format_bundle_summary, ToolRegistry

### Verificacion
- [x] `uv run ruff check .` — All checks passed
- [x] `uv run pytest --no-cov` — 510 passed, 11 skipped

### Protocolo fin de sesion
- [x] `docs/PROGRESS.md` — actualizar estado
- [x] `docs/CHANGELOG.md` — registrar cambios
- [x] `docs/ROADMAP.md` — marcar 4.9 como completada
- [x] `tasks/todo.md` — marcar tareas completadas
