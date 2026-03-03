# ADR-003: Python-first con Polyglot Estratégico

**Estado:** Aceptada
**Fecha:** 2026-03-03
**Autor:** Fede

## Contexto

El desarrollador tiene 12+ años de experiencia en JVM (Scala/Java) y está en transición a AI Engineering. El ecosistema de AI/LLM es mayoritariamente Python-first. Sin embargo, hay componentes donde Python no es la mejor opción (CLI distribuible, UIs ricas, procesamiento CPU-bound).

## Decisión

Python 3.12+ es el lenguaje principal para toda la Etapa 1 y el core del proyecto. Componentes específicos pueden implementarse en otros lenguajes cuando exista un benchmark concreto que lo justifique.

Lenguajes aprobados como "escapatorias estratégicas":
- **Rust** (vía PyO3): componentes de alto rendimiento (terminology trie, document processing)
- **TypeScript** (React/Next.js): dashboards y UIs (Etapa 3+)
- **Go**: CLIs distribuibles como single binary (solo si se necesita)

## Consecuencias

### Positivas
- Velocidad de iteración máxima con un solo desarrollador
- Acceso directo a todo el ecosistema LLM/AI (Anthropic SDK, Langfuse, MCP SDK)
- UV + Ruff resuelven los problemas históricos de Python
- La comunidad de health informatics es Python/R
- Prototipado rápido: crucial para validar el agente contra benchmarks

### Negativas
- Python es lento para CPU-bound tasks (mitigable con Rust vía PyO3 cuando se necesite)
- Type system menos estricto que JVM (mitigable con mypy strict + Pydantic)
- No se aprovecha la experiencia JVM del desarrollador directamente (pero se transfiere el design thinking)

### Riesgos
- Si el terminology resolver necesita procesar millones de conceptos SNOMED en < 1s, Python no alcanza. Trigger: benchmark > 5s para resolution → evaluar Rust binding.
- Si la comunidad MCP migra a TypeScript-only, habría que portar el server. Probabilidad baja dado que Anthropic mantiene el Python SDK.

## Alternativas consideradas

### Kotlin/Scala (JVM) como lenguaje principal
- Pros: Experiencia del desarrollador, HAPI FHIR es Java nativo, type safety fuerte
- Contras: Ecosistema LLM/AI es Python-first; Anthropic SDK, Langfuse, MCP SDK no tienen soporte JVM oficial; duplica esfuerzo de integración

### TypeScript como lenguaje principal
- Pros: MCP SDK nativo, unificación frontend/backend, npm ecosystem
- Contras: Librerías FHIR menos maduras que Python, no hay equivalente a fhir.resources (Pydantic models), ecosistema AI menos maduro

### Go como lenguaje principal
- Pros: Compilación rápida, binarios estáticos, excelente para CLI tools
- Contras: Ecosistema FHIR inexistente, verbose para data transformation, no hay FHIR model library, ecosistema LLM pobre

## Referencias

- [UV workspace docs](https://docs.astral.sh/uv/concepts/workspaces/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [fhir.resources (Python FHIR models)](https://github.com/nazrulworld/fhir.resources)
- [Verily FHIR-AgentBench — implemented in Python](https://github.com/google-health/fhir-agentbench)
