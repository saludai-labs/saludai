# SaludAI — TODO (Sesion actual)

> Actualizar al inicio de cada sesion con las tareas concretas.
> Marcar como completadas durante la sesion.

## Sesion: Sprint 3, Sesion 3.6 — FHIR Awareness en Locale Packs

### Implementacion Level 1 (Awareness)

- [x] Extender `_types.py` con 6 dataclasses nuevos: FHIRProfileDef, ExtensionDef, CustomOperationDef, CustomSearchParamDef, IdentifierSystemDef, LocaleResourceConfig
- [x] Extender `LocalePack` con 7 campos nuevos (defaults vacios = backward-compatible)
- [x] Poblar AR pack con datos reales de openRSD/AR.FHIR.CORE (profiles, extensions, identifiers, operations, resource configs)
- [x] Generador de seccion de prompt desde locale pack metadata (`_prompt_builder.py`)
- [x] Integrar seccion generada en el system prompt de AR
- [x] Tests: tipos nuevos, AR pack, prompt builder (37 tests nuevos, 449 total)
- [x] Actualizar `LOCALE_GUIDE.md` con los nuevos campos
- [x] Actualizar `__init__.py` re-exports

### Documentacion y planificacion

- [x] Crear ADR-008: FHIR Awareness en Locale Packs
- [x] Actualizar ROADMAP.md — agregar sesion 3.6
- [x] Actualizar backlog con items de Level 2 (ejecucion)
- [x] Protocolo fin de sesion (PROGRESS.md, CHANGELOG.md, etc.)
