# SaludAI — Estado Actual

**Última actualización:** 2026-03-03
**Sprint actual:** Sprint 2 — El Cerebro del Agente
**Sesión actual:** 2.2 — FHIR Query Builder (completada)

---

## Estado General

🟢 **Sprint 1 completo** — Monorepo configurado, CI activo, Docker Compose con HAPI FHIR R4, FHIR client funcional, repo presentable para público.
🟢 **Sesión 2.1 completa** — TerminologyResolver implementado con SNOMED CT AR (~96 códigos), CIE-10 (~45 códigos), LOINC (~30 códigos). Fuzzy matching con rapidfuzz. 35 tests nuevos, todos verdes.
🟢 **Sesión 2.2 completa** — FHIR Query Builder implementado. Frozen dataclasses para params, fluent builder API, factory shortcuts (snomed, loinc, cie10), soporte para chained params, _include/_revinclude, _sort, _count, _total, _elements. 96 tests nuevos, todos verdes.

## Última Sesión Completada

**Sprint 2, Sesión 2.2** — FHIR Query Builder

### Lo que se hizo
- `saludai_core/exceptions.py` — Agregados `QueryBuilderError`, `QueryBuilderValidationError`
- `saludai_core/query_builder.py` — Módulo principal (~400 líneas):
  - Enums: `FHIRResourceType` (15 resource types), `DatePrefix` (8 prefijos), `SortOrder`
  - Frozen dataclasses: `TokenParam`, `DateParam`, `ReferenceParam`, `QuantityParam`, `StringParam`, `IncludeParam`, `SortParam`
  - Todos con método `to_fhir() -> str` para serialización FHIR
  - `FHIRQuery` — output inmutable con `to_params() -> dict[str, str | list[str]]`
  - Factory functions: `token()`, `snomed()`, `loinc()`, `cie10()`, `date_param()`, `reference()`, `quantity()`
  - `FHIRQueryBuilder` — API fluent: `where()`, `where_token()`, `where_date()`, `where_reference()`, `where_string()`, `include()`, `revinclude()`, `sort()`, `count()`, `total()`, `elements()`, `build()`
  - Validación: resource types, formato ISO 8601, params no vacíos, _count positivo, _total válido
- `saludai_core/__init__.py` — Re-exports de todos los tipos nuevos + excepciones
- `tests/test_query_builder.py` — 96 tests en 13 clases:
  - FHIRResourceType (7), TokenParam (6), DateParam (10), ReferenceParam (2), QuantityParam (4), StringParam (3), IncludeParam (3), SortParam (3), FHIRQueryBuilder (21), FHIRQueryToParams (6), ChainedParams (3), Golden (7), ExceptionHierarchy (2)

### Verificación
- `uv run pytest packages/saludai-core/` → 131 passed (96 nuevos + 35 terminology)
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → All files formatted
- Golden tests: diabetes+edad, laboratorio glucosa, Buenos Aires, medicaciones activas, CIE-10, revinclude, quantity

## Sprint 1 — Completado

Todas las sesiones del Sprint 1 están finalizadas:
- ✅ 1.1 — Monorepo UV + estructura de paquetes
- ✅ 1.2 — GitHub Actions CI + pre-commit hooks
- ✅ 1.3 — Docker Compose: HAPI FHIR R4 + datos sintéticos argentinos
- ✅ 1.4 — saludai-core: FHIR client (connect, search, read)
- ✅ 1.5 — README, LICENSE, CONTRIBUTING.md

## Sprint 2 — En Progreso

- ✅ 2.1 — Terminology Resolver (SNOMED CT AR, CIE-10, LOINC)
- ✅ 2.2 — FHIR Query Builder
- ⬜ 2.3 — Agent Loop v1
- ⬜ 2.4 — Langfuse integration
- ⬜ 2.5 — FHIR-AgentBench baseline

## Próxima Sesión

**Sprint:** 2 — El Cerebro del Agente
**Sesión:** 2.3 — Agent Loop v1 (single-turn: plan → execute → evaluate)
**Objetivo:** Prompt en lenguaje natural → consulta FHIR → respuesta narrativa
**Referencia:** `docs/ROADMAP.md` → Sprint 2 → Sesión 2.3

## Blockers

Ninguno.

## Decisiones Tomadas

- GitHub Org: `saludai-labs` (confirmado)
- Git remote via HTTPS (no SSH)
- Root pyproject.toml es workspace virtual (sin build-system)
- `dependency-groups.dev` para dev-dependencies (estándar actual de UV)
- CI: Python 3.12 single version (sin matrix — no agrega valor todavía)
- CI: Sin mypy por ahora (no hay código real que tipar)
- CI: Sin coverage enforcement (no hay tests sustanciales)
- Pre-commit: `ruff-pre-commit` oficial (no ruff via sistema)
- Pytest: `--import-mode=importlib` para monorepos con test files homónimos
- **Langfuse Cloud (free tier)** en vez de self-hosted (ADR-006)
- **HAPI FHIR con H2 en memoria** — datos efímeros, sin PostgreSQL extra
- **fhir.resources default** — compatible con R4, sin sub-módulo específico
- **TerminologyResolver sync** — todo es CPU en memoria, no necesita async
- **CSVs embebidos** — legibles, diffeables, editables por no-programadores
- **rapidfuzz** — ~10x más rápido que difflib, provee token_sort_ratio + partial_ratio
- **Scores 0-100** — consistente con escala de rapidfuzz (EXACT_MATCH_SCORE = 100.0)
- **No stripear acentos** — rapidfuzz maneja variantes naturalmente
- **QueryBuilder puramente sync** — solo transforma datos, no hace I/O
- **Frozen dataclasses** para todos los param types — inmutabilidad garantizada
- **Factory shortcuts** (snomed, loinc, cie10) — ergonomía sin perder tipado
- **validate=False escape hatch** — permite resource types custom sin romper API

## Decisiones Pendientes

- [ ] Licencia exacta del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)
