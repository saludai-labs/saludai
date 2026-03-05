# ADR-007: Sistema de Locale Packs

**Estado:** Aceptada
**Fecha:** 2026-03-05
**Autor:** Fede

## Contexto

SaludAI tiene toda la configuración específica de Argentina hardcodeada: CSVs de terminología en `saludai_core/data/`, system prompt en español argentino, descripciones de tools en español, enum de sistemas de terminología. Esto impide extender el agente a otros países/regiones de LATAM sin duplicar código.

Necesitamos un mecanismo para empaquetar toda la configuración locale-específica de manera extensible, sin romper la API existente.

## Decisión

Implementamos un sistema de **locale packs** como frozen dataclasses inmutables:

- `TerminologySystemDef`: define un sistema de terminología (key, URI, CSV, package).
- `LocalePack`: agrupa toda la configuración de un país/región (terminología, prompt, tool descriptions, enums).
- `load_locale_pack(code)`: factory que carga un pack por código (default: `"ar"`).
- Argentina (`"ar"`) viene bundled como el único pack built-in.
- Los CSVs se mueven de `saludai_core/data/` a `saludai_core/locales/ar/`.

### Selección de locale

- Variable de entorno `SALUDAI_LOCALE=ar` → `AgentConfig.locale` → `load_locale_pack("ar")`.
- Default: `"ar"` — zero behavior change para usuarios existentes.
- Futuro (backlog): discovery via `importlib.metadata.entry_points(group="saludai.locales")`.

## Consecuencias

### Positivas
- **Extensibilidad clara**: agregar un nuevo país es crear un nuevo locale pack (no tocar código del agente)
- **Backward compatible**: AR como default, sin cambios en API existente
- **Inmutable**: frozen dataclasses previenen mutación accidental
- **Demostrable**: el README puede mostrar multi-país como feature diferenciadora
- **Testeable**: cada pack es una constante que se puede validar independientemente

### Negativas
- ~~Los CSVs ahora están duplicados temporalmente (data/ y locales/ar/) hasta que se limpie data/ (backlog)~~ **Resuelto en sesion 4.6:** `data/` eliminado, `locales/ar/` es la unica fuente.
- Agregar un pack requiere conocimiento de la estructura interna (mitigado con LOCALE_GUIDE.md)

### Riesgos
- Si los packs crecen mucho (100+ conceptos), el import time podría aumentar. Mitigable con lazy loading.

## Alternativas consideradas

### 1. Configuración via YAML/JSON externo
- Pros: No requiere código Python
- Contras: Pierde type safety, no se puede bundlear con el package, más difícil de validar

### 2. Subclases / herencia
- Pros: Familiar pattern OOP
- Contras: Overengineered para datos estáticos; hace testing más complejo

### 3. Entry points desde el inicio
- Pros: Máxima extensibilidad
- Contras: Premature abstraction — no tenemos un segundo locale todavía. Mejor preparar la interfaz y activar entry points cuando haya demanda real.
