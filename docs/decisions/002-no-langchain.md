# ADR-002: No LangChain — Custom Agent Loop

**Estado:** Aceptada
**Fecha:** 2026-03-03
**Autor:** Fede

## Contexto

Para implementar el FHIR Smart Agent (Módulo 1), necesitamos un agent loop que orqueste llamadas LLM, ejecución de tools, y razonamiento multi-turn. Existen frameworks populares (LangChain, LlamaIndex, CrewAI) que ofrecen abstracciones para esto.

Sin embargo, SaludAI opera en el dominio clínico donde la **auditabilidad** y **trazabilidad** de cada decisión del agente son requisitos no negociables. Necesitamos control total sobre:
- Qué se envía al LLM en cada iteración
- Cómo se procesan y validan los resultados de tools
- Qué se loguea y tracea en Langfuse
- Cómo se manejan errores y retries

## Decisión

Implementar un **agent loop custom** en `saludai-agent` sin depender de LangChain, LangGraph, LlamaIndex, CrewAI, ni ningún framework de agentes.

El loop usa **native tool calling** del LLM provider (Anthropic/OpenAI) directamente, con una abstracción `LLMClient` propia que es provider-agnostic.

## Consecuencias

### Positivas
- **Auditabilidad total:** Cada paso del loop es código propio, inspeccionable y testeable
- **Trazabilidad:** Instrumentación explícita con Langfuse — cada generation, tool call, y decisión tiene su span
- **Sin abstracciones opacas:** No hay "chains" ni "runnables" ni "agents" mágicos entre nuestro código y el LLM
- **Provider-agnostic real:** Nuestra `LLMClient` interface soporta Anthropic, OpenAI, y Ollama sin adaptadores de terceros
- **Testing simple:** El loop es una clase Python estándar, se testea con mocks directos
- **Sin dependencias transitivas:** LangChain trae ~50 dependencias; nuestro agent tiene ~5
- **Evolución libre:** Podemos cambiar la arquitectura del loop sin esperar releases de un framework

### Negativas
- **Más código propio:** El agent loop, tool registry, y message handling son ~500 líneas nuestras
- **Sin ecosistema de plugins:** No podemos usar "LangChain tools" o "LangChain retrievers" directamente
- **Documentación interna necesaria:** Debemos documentar bien nuestro propio loop para nuevos contribuidores

### Riesgos
- Si la complejidad del agente crece mucho (multi-agent, planning, etc.), mantener el loop custom puede ser costoso
- Mitigación: El diseño modular (LLMClient, ToolRegistry, Tracer) permite refactorizar sin reescribir todo

## Alternativas consideradas

### Opción A: LangChain / LangGraph
- Pros: Ecosistema grande, muchos ejemplos, integración nativa con LangSmith
- Contras: Abstracciones pesadas y opacas, ~50 dependencias transitivas, cambios breaking frecuentes, difícil de debugear, LangSmith lock-in para tracing

### Opción B: LlamaIndex
- Pros: Buen soporte para RAG y query engines
- Contras: Orientado a RAG/search, no a agent loops con tools FHIR; abstracciones igualmente opacas

### Opción C: CrewAI
- Pros: Multi-agent nativo, roles/tasks
- Contras: Overkill para un solo agente, dependencia de LangChain internamente, menos control sobre prompts

### Opción D: Custom (elegida)
- Pros: Control total, mínimas dependencias, auditabilidad, testing simple
- Contras: Más código propio a mantener

## Referencias

- `packages/saludai-agent/src/saludai_agent/loop.py` — implementación del agent loop
- `packages/saludai-agent/src/saludai_agent/llm.py` — LLMClient protocol + providers
- `packages/saludai-agent/src/saludai_agent/tools.py` — ToolRegistry
- [Anthropic tool use docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [OpenAI function calling docs](https://platform.openai.com/docs/guides/function-calling)
