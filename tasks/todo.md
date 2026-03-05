# SaludAI — TODO (Sesion actual)

> Actualizar al inicio de cada sesion con las tareas concretas.
> Marcar como completadas durante la sesion.

## Sesion: Sprint 4, Sesion 4.7 — Locale pack discovery via `entry_points`

### 1. Implementar discovery en `load_locale_pack()`
- [x] Usar `importlib.metadata.entry_points(group="saludai.locales")` como fallback
- [x] Actualizar `available_locales()` para incluir packs externos
- [x] Validar que el entry point retorna un `LocalePack` valido

### 2. Documentar el mecanismo
- [x] Actualizar docstrings en `locales/__init__.py`
- [x] Actualizar `docs/LOCALE_GUIDE.md` con instrucciones de entry_points

### 3. Tests
- [x] Test: entry point discovery con mock de `importlib.metadata`
- [x] Test: `available_locales()` incluye packs externos
- [x] Test: entry point invalido (no es LocalePack) lanza error
- [x] Test: built-in tiene prioridad sobre entry point con mismo code
- [x] Test: `LocaleNotFoundError` cuando no hay pack ni entry point
- [x] Test: error message lista todos los locales disponibles

### Verificacion
- [x] `uv run ruff check .` — sin errores
- [x] `uv run pytest --no-cov` — 479 passed, 11 skipped

### Protocolo fin de sesion
- [x] `docs/PROGRESS.md` — actualizar estado
- [x] `docs/CHANGELOG.md` — registrar cambios
- [x] `docs/ROADMAP.md` — marcar 4.7 como completada
- [x] `tasks/todo.md` — marcar tareas completadas
- [x] `tasks/backlog.md` — marcar item completado
