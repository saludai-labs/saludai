# ADR-009: Hybrid Query Planner (Plan-and-Execute)

**Estado:** Aceptada
**Autor:** SaludAI

## Contexto

El agente usa un loop ReAct naive donde el LLM decide ad-hoc que herramientas llamar. Esto funciono bien con datos pequenos (55 pacientes, 98% accuracy) pero al escalar a 200 pacientes y 100 preguntas, la accuracy cayo a 79%.

El problema principal: el LLM no aprovecha las capacidades avanzadas de FHIR search (`_has`, `_summary=count`, `_include`) de forma consistente, resultando en queries sub-optimas que transfieren datos innecesarios y requieren muchas iteraciones.

Necesitamos que el agente "conozca" FHIR a nivel de query planning, no solo a nivel de ejecucion.

### Restricciones

- No LangChain (ADR-002) — el planner debe ser parte del loop custom
- Extensible por locale (ADR-007) — el conocimiento FHIR puede variar por pais
- Auditable (Langfuse) — el plan debe ser trazable
- Costo razonable — no duplicar el gasto en LLM calls

## Decision

Implementar un **Hybrid Query Planner** con patron Plan-and-Execute:

1. **Planning phase**: 1 LLM call (sin tools) que clasifica la pregunta y selecciona una estrategia de un catalogo estructurado de patrones FHIR
2. **Execution phase**: El loop ReAct existente, con el plan inyectado como contexto en el system prompt
3. **Fallback**: Si la estrategia planificada no produce resultados, el executor cae al ReAct libre

El conocimiento FHIR se modela como datos estructurados, no como texto en el prompt:
- **Grafo de referencias**: `ResourceRelationship` dataclass con las aristas entre resource types
- **Catalogo de patrones**: ~10 templates de query FHIR (count, search, aggregate, etc.)
- **Ambos inyectados en el planner prompt** como contexto compacto

El LLM se encarga de la parte fuzzy (clasificacion NLP, extraccion de terminos). El catalogo se encarga de la parte precisa (sintaxis FHIR valida, patrones probados).

### Nuevo tool: `count_fhir`

Tool dedicado para server-side counting que siempre agrega `_summary=count`. Soporta `_has` para conteos cross-resource sin transferir datos.

### Evolucion

El diseno soporta escalamiento gradual:
- Catalogo actual (~15 patrones) -> RAG con vector store cuando supere 50 patrones
- Grafo actual (adjacency list) -> Graph DB cuando supere 30 resource types con cadenas 4+ hops
- Terminologia actual (rapidfuzz) -> Embeddings medicos cuando supere 1000 conceptos

## Consecuencias

### Positivas

- Mejor accuracy: el agente elige queries optimas desde el inicio
- Menor costo: `_summary=count` evita transferir datos para ~60% de preguntas
- Menos iteraciones: 1-2 en vez de 3-5 para preguntas con plan claro
- Testeable: catalogo de patrones es determinista y verificable con unit tests
- Extensible: nuevos resource types se agregan al grafo, nuevos patrones al catalogo
- Auditable: el plan (JSON) se loguea en Langfuse como un span separado

### Negativas

- +1 LLM call por query (~$0.01-0.03, compensado por menos iteraciones)
- Mas complejidad en el loop (2 fases en vez de 1)
- El catalogo necesita mantenimiento cuando se agregan resource types

### Riesgos

- El planner podria clasificar mal una pregunta -> mitigado por fallback a ReAct
- El catalogo podria no cubrir un caso nuevo -> mitigado por fallback a ReAct
- El costo incremental del planner call podria no compensarse -> medir en benchmark

## Alternativas consideradas

### Opcion A: Pure LLM (todo en prompt)

Todo el conocimiento FHIR como texto en el system prompt. El LLM razona solo.

- Pros: Minimo codigo, flexible
- Contras: LLM olvida/distorsiona sintaxis FHIR, caro en tokens, no testeable

### Opcion B: Pure Internal Model (reglas)

Motor de reglas deterministico que mapea preguntas a queries sin LLM.

- Pros: Deterministico, rapido, costo 0
- Contras: No puede clasificar lenguaje natural, fragil ante preguntas nuevas

### Opcion C: Full RAG + Graph DB + Vector Store

Vector store (Chroma) para patrones, Neo4j para relaciones FHIR, embeddings para terminologia.

- Pros: Escala a miles de patrones y terminologias
- Contras: Overkill para ~15 patrones y ~170 codigos, agrega 3 dependencias de infra

## Referencias

- Diseno completo: `docs/knowledge/fhir-query-planner-design.md`
- Wang et al. 2023: "Plan-and-Solve Prompting"
- FHIR R4 Search: https://hl7.org/fhir/R4/search.html
- ADR-002: No LangChain
- ADR-007: Locale packs
- ADR-008: FHIR Awareness
