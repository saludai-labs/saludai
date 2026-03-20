# ADR-002: No LangChain — Custom Agent Loop

**Estado:** Aceptada
**Autor:** SaludAI

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

## Re-evaluacion: Sprint 5 — ¿Conviene migrar a LangGraph?

**Fecha:** 2026-03-11
**Veredicto:** No. La decision se mantiene.

### Contexto de la re-evaluacion

Para Sprint 5 el agent loop acumulo varias extensiones que LangGraph ofrece
como primitivas de primera clase:

| Feature | Nuestro codigo | LangGraph equivalente |
|---------|---------------|----------------------|
| ReAct loop | `loop.py` (~200 loc) | `create_react_agent()` |
| Working memory | `store` dict (10 loc) | `StateGraph` con `TypedDict` |
| Plan-and-Execute | `planner.py` (~150 loc) | `PlanExecute` pattern |
| Action Space Reduction | Tool filtering (~30 loc en loop) | Conditional edges + tool nodes |
| Tracing | Langfuse protocol (~100 loc) | LangSmith nativo o callbacks |
| Checkpointing/resume | JSONL manual (~50 loc) | `SqliteSaver` / `PostgresSaver` |

Total custom: **~500 loc**. Cada pieza es individualmente simple (<50 lineas),
testeable de forma aislada, y entendible en 2 minutos.

### Por que NO migrar

**1. Complejidad real vs complejidad percibida**

La pregunta "¿no deberiamos usar LangGraph?" surge cuando uno ve la lista de
features custom. Pero la complejidad real de cada una es baja:

- `store` = 10 lineas (un dict + inyeccion en globals)
- Planner = 1 LLM call que retorna JSON, sin orquestacion
- ASR = filtrar una lista de tools segun el plan
- Tracing = protocol con 5 metodos, implementaciones de ~40 loc cada una

LangGraph resolveria todo esto, pero a cambio introduce:
- Un grafo con nodos, edges, conditional routing, state reducers
- Conceptos como `Channels`, `Reducers`, `Checkpoints`
- Dependencia de `langchain-core` (~50 deps transitivas)

Es cambiar complejidad **accidental** (nuestras 500 loc) por complejidad
**esencial** del framework (aprender, mantener, y debugear un grafo de estado).
Para un solo agente ReAct, es overkill.

Ref: Brooks (1986) "No Silver Bullet" — la distincion entre complejidad esencial
y accidental. Un framework solo es util si reduce complejidad esencial, no si
solo reemplaza complejidad accidental por otra equivalente.

**2. Auditabilidad en contexto clinico**

El argumento original de ADR-002 no solo sigue vigente — se refuerza. Con las
extensiones del Sprint 5 (planner, ASR, store), cada pieza tiene tests
unitarios directos, logs estructurados, y trazas en Langfuse con granularidad
de linea. En LangGraph, el debugging pasa por inspeccionar el estado del grafo,
lo cual agrega una capa de indirection.

Para un sistema que procesa datos clinicos, "puedo leer cada linea de codigo
que toca mis datos" es un feature, no un bug.

**3. Estabilidad de dependencias**

El ecosistema LangChain tiene un historial de breaking changes frecuentes
(v0.1 → v0.2 → v0.3 en ~12 meses, cada una con cambios de API). Para un
proyecto que va a PyPI y sera usado por terceros, anclar una dependencia
volatil es riesgoso.

Nuestras dependencias core (`httpx`, `pydantic`, `langfuse`) tienen APIs
estables con versionado semantico real.

**4. La regla del "si lo puedo escribir en un dia, no necesito un framework"**

Cada extension que agregamos tomo 1-2 horas. El total acumulado es ~1 dia de
trabajo. LangGraph tomaria ~1 dia de setup + aprendizaje + migracion, y luego
estariamos atados al framework para siempre.

### Cuando SI migrariamos

La decision se invierte si el proyecto necesita alguno de estos:

- **Multi-agent**: modulo 2+ con agentes especializados que colaboran
- **Human-in-the-loop**: aprobacion clinica antes de ejecutar acciones
- **Long-running workflows**: tareas que duran horas con checkpointing robusto
- **Branching condicional complejo**: >3 paths de ejecucion con backtracking

En ese caso, el grafo de estado de LangGraph justificaria su complejidad.
Pero eso es problema del futuro (Modules 2-5), no del presente (Module 1).

Ref: YAGNI (Beck, 1999) — "You Aren't Gonna Need It". Implementar para
requisitos hipoteticos futuros aumenta la complejidad presente sin garantia
de que esos requisitos se materialicen.

---

## Referencias

### Codigo
- `packages/saludai-agent/src/saludai_agent/loop.py` — agent loop (~200 loc)
- `packages/saludai-agent/src/saludai_agent/llm.py` — LLMClient protocol + providers
- `packages/saludai-agent/src/saludai_agent/tools.py` — ToolRegistry + store
- `packages/saludai-agent/src/saludai_agent/planner.py` — Query Planner

### APIs y frameworks
- [Anthropic tool use docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [OpenAI function calling docs](https://platform.openai.com/docs/guides/function-calling)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/) — para referencia de lo que NO usamos y por que

### Teoria
- Brooks (1986) "No Silver Bullet — Essence and Accident in Software Engineering"
- Beck (1999) "Extreme Programming Explained" — principio YAGNI

### ADRs relacionados
- ADR-009: Hybrid Query Planner
- ADR-010: Scratchpad Working Memory
