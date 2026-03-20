# ADR-004: Langfuse para Observabilidad

**Estado:** Aceptada
**Autor:** SaludAI

## Contexto

El FHIR Smart Agent necesita observabilidad completa: trazas de cada llamada LLM, ejecución de tools, latencias, tokens consumidos, y resultados. Esto es crítico para:

1. **Debugging:** Entender por qué el agente tomó una decisión incorrecta
2. **Benchmarking:** Comparar cambios de prompt/tools con métricas trazables
3. **Auditoría clínica:** En producción, cada consulta médica debe ser rastreable
4. **Optimización de costos:** Monitorear consumo de tokens por query

Necesitamos una plataforma de observabilidad para LLM que soporte tracing jerárquico (trace → generation → tool call).

## Decisión

Usar **Langfuse** como plataforma de observabilidad para todas las interacciones LLM del agente.

La integración es a través de un `Tracer` protocol propio (no el SDK decorator de Langfuse), lo que mantiene el código desacoplado del provider de observabilidad.

> **Nota:** La decisión de usar Langfuse Cloud vs self-hosted se documenta por separado en ADR-006.

## Consecuencias

### Positivas
- **Open source:** Langfuse es open source (MIT), alineado con los valores del proyecto
- **Tracing jerárquico:** Soporta trace → span → generation con metadata arbitraria
- **Dashboard completo:** Visualización de latencias, costos, scores, filtros por metadata
- **Evaluaciones integradas:** Soporte nativo para scores/evaluaciones (útil para benchmark)
- **Multi-provider:** Funciona con Anthropic, OpenAI, Ollama — no está atado a un LLM vendor
- **Free tier generoso:** 50k observaciones/mes en cloud, sin límite en self-hosted
- **SDK Python:** `langfuse` SDK oficial con buen soporte async

### Negativas
- **Dependencia externa:** Una librería más en el stack (aunque opcional via `NoOpTracer`)
- **Latencia de envío:** ~100ms extra por trace cuando se usa cloud (batch async mitiga esto)
- **Curva de aprendizaje:** El modelo de tracing (traces, spans, generations) tiene su complejidad

### Riesgos
- Si Langfuse cambia su modelo de pricing o deja de mantenerse, necesitaríamos migrar
- Mitigación: Nuestro `Tracer` protocol permite implementar un adapter a cualquier otro backend (Phoenix, LangSmith, custom) sin cambiar el agent code

## Alternativas consideradas

### Opción A: LangSmith
- Pros: Integración nativa con LangChain, dashboard maduro
- Contras: Propietario (no open source), pricing agresivo, lock-in con LangChain ecosystem; no usamos LangChain (ADR-002)

### Opción B: Arize Phoenix
- Pros: Open source, buen soporte para evaluaciones
- Contras: Más orientado a ML ops genérico que a LLM tracing, menor ecosistema, setup más complejo

### Opción C: Custom logging (structlog + archivos)
- Pros: Sin dependencias externas, control total
- Contras: Sin dashboard, sin evaluaciones integradas, requiere construir toda la infraestructura de visualización y análisis

### Opción D: OpenTelemetry + Grafana
- Pros: Estándar abierto, infraestructura madura
- Contras: No tiene abstracciones LLM-native (generations, tokens, prompts), mucho esfuerzo de integración para nuestro caso de uso

## Referencias

- `packages/saludai-agent/src/saludai_agent/tracing.py` — Tracer protocol + LangfuseTracer + NoOpTracer
- `docs/decisions/006-langfuse-cloud.md` — decisión Cloud vs self-hosted
- `docs/knowledge/langfuse-setup.md` — investigación inicial
- [Langfuse docs](https://langfuse.com/docs)
- [Langfuse GitHub](https://github.com/langfuse/langfuse)
