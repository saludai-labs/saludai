# ADR-001: Monorepo con UV Workspaces

**Estado:** Aceptada
**Autor:** SaludAI

## Contexto

SaludAI tiene 4 paquetes (core, agent, mcp, api) que comparten tipos, configuración e infraestructura. Necesitamos decidir si van en repos separados o en un monorepo.

## Decisión

Monorepo con UV workspaces. Todos los paquetes Python viven en `packages/` dentro de un solo repositorio.

## Consecuencias

### Positivas
- Cambios cross-package en un solo PR (ej: cambiar un tipo en core y actualizar agent)
- CI unificado — un pipeline testea todo
- Refactors atómicos sin coordinar entre repos
- `uv sync` instala todo el workspace de una vez
- Un solo CLAUDE.md con contexto completo

### Negativas
- CI más lento a medida que crece (mitigable con path filtering)
- Un issue en un paquete puede bloquear CI de todos
- PyPI publishing requiere scripts por paquete

### Riesgos
- Si el monorepo crece mucho (+10 paquetes), la complejidad de CI puede ser un problema. Reevaluar en Etapa 3.

## Alternativas consideradas

### Multi-repo (un repo por paquete)
- Pros: CI independiente, releases independientes, más familiar para contribuidores
- Contras: Cambios cross-package requieren múltiples PRs coordinados; versioning hell; setup local complejo

### Multi-repo con Git submodules
- Pros: Agrupa sin acoplar
- Contras: Submodules son notoriamente frágiles; complejidad innecesaria para 4 paquetes
