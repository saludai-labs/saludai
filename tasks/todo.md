# SaludAI — TODO (Sesion actual)

> Actualizar al inicio de cada sesion con las tareas concretas.
> Marcar como completadas durante la sesion.

## Sesion: Sprint 4, Sesion 4.8 — Parametro `_has` (reverse chaining) en Query Builder

### 1. Implementar `HasParam` dataclass + `has()` method
- [x] `HasParam` frozen dataclass: `resource_type`, `search_param`, `target_param`, `value` (ParamValue | str)
- [x] `FHIRQueryBuilder.has()` method con fluent API
- [x] Validacion de parametros vacios

### 2. Exportar en `__init__.py`
- [x] Agregar `HasParam` a los exports de `query_builder.py`
- [x] Agregar `HasParam` a imports y `__all__` del `__init__.py` de saludai-core

### 3. Tests
- [x] Test basico: `Patient?_has:Condition:subject:code=snomed`
- [x] Test con value como ParamValue (TokenParam, DateParam)
- [x] Test con value como string plano
- [x] Test multiple `_has` (Patient con Condition + Observation)
- [x] Test parametros vacios lanzan error (3 tests)
- [x] Test golden: 2 queries clinicas realistas con `_has`
- [x] Test chaining: `.has()` retorna self
- [x] Test frozen: HasParam es inmutable
- [x] Test combinado con otros params (address-state + _has + _count)

### 4. Verificacion
- [x] `uv run ruff check .` — All checks passed
- [x] `uv run pytest --no-cov` — 495 passed

### Protocolo fin de sesion
- [x] `docs/PROGRESS.md` — actualizar estado
- [x] `docs/CHANGELOG.md` — registrar cambios
- [x] `docs/ROADMAP.md` — marcar 4.8 como completada
- [x] `tasks/todo.md` — marcar tareas completadas
- [x] `tasks/backlog.md` — marcar item completado
