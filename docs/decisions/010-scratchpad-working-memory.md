# ADR-010: Scratchpad Working Memory para el Agent Loop

**Estado:** Aceptada
**Autor:** SaludAI
**Fecha:** 2026-03-11

## Contexto

### El problema: re-busqueda en queries cross-resource

El agent loop usa un scratchpad `entries` que contiene los recursos FHIR de la
**ultima** busqueda. Cuando una pregunta requiere cruzar datos de 2+ busquedas
(ej: "pacientes con DM2 que tienen glucosa > 140"), el agente pierde los
resultados de la primera busqueda al hacer la segunda porque `entries` se
sobreescribe.

Esto causa un patron de **re-busqueda**: el agente repite las mismas queries
FHIR multiples veces para recuperar datos que ya habia obtenido. Evidencia del
benchmark (Exp 7, 20q sample):

| Pregunta | Iteraciones | Problema |
|----------|-------------|----------|
| C10 (DM2 + glucosa > 140) | 10 | Re-busca Conditions 3x, Observations 2x |
| C45 (HTA + PA > 140 en BA) | 12 | Re-busca Conditions 3x, Observations 2x |
| C05 (menores 18 + condiciones) | 12 (max, fallo) | No puede cruzar edad + condiciones |
| C30 (DM2 sin HbA1c) | 12 (max, fallo) | No puede hacer negacion cross-resource |

Las re-busquedas representan ~60% del costo en queries cross-resource ($0.10+
por pregunta vs $0.02-0.05 para queries simples). Dos preguntas directamente
fallan por max_iterations porque el agente entra en un loop de buscar → perder
datos → buscar de nuevo.

---

## Marco teorico: Memoria en LLM Agents

### Taxonomia de memoria en agentes

La literatura de LLM agents distingue varios tipos de memoria, en analogia con
la psicologia cognitiva (Atkinson & Shiffrin, 1968):

| Tipo | Analogia cognitiva | En LLM agents | En SaludAI |
|------|-------------------|---------------|------------|
| **Sensory memory** | Buffer sensorial | Token window actual | Input del usuario |
| **Short-term / Working memory** | Manipulacion activa | Scratchpad, notepad | `entries` + `store` |
| **Long-term memory** | Almacenamiento duradero | Vector stores, RAG | Terminology CSVs, FHIR knowledge graph |
| **Episodic memory** | Recuerdos de eventos | Historial de conversacion | Message history en el loop |
| **Semantic memory** | Conocimiento general | Pesos del modelo | Conocimiento de FHIR en el LLM |
| **Procedural memory** | Saber-hacer | System prompt, tools | Prompt + tool definitions |

Ref: Park et al. (2023) "Generative Agents: Interactive Simulacra of Human Behavior"
clasifica estos tipos en agentes con LLMs.

### El patron Scratchpad

**Scratchpad Memory** (Nye et al., 2021 - "Show Your Work: Scratchpads for
Intermediate Computation with Language Models") demostro que dar a un LLM un
espacio de escritura intermedia mejora significativamente su capacidad de
razonamiento multi-paso. En su estudio, tareas aritmeticas que el modelo fallaba
se resolvian correctamente cuando podia escribir pasos intermedios.

La idea clave: **el context window del LLM es como la memoria de trabajo humana
— limitada**. Si un paso intermedio se pierde (por sobreescritura o por salir
del contexto), el modelo debe recalcular desde cero. Un scratchpad explicito
permite "externalizar" resultados intermedios.

### Variantes del patron en la literatura

1. **ReAct Notepad** (Yao et al., 2022 - "ReAct: Synergizing Reasoning and
   Acting in Language Models"): El agente alterna entre razonamiento (Thought)
   y accion (Action). El "notepad" es el trace de thoughts+observations que
   se acumula en el contexto. Limitacion: crece linealmente y puede desbordar
   el context window.

2. **Toolformer Working Memory** (Schick et al., 2023 - "Toolformer: Language
   Models Can Teach Themselves to Use Tools"): El modelo aprende a insertar
   llamadas a herramientas en su propia generacion. Los resultados se insertan
   inline. No hay separacion explicita entre working memory y output.

3. **Agent State** (LangGraph / LangChain): Estado tipado (`TypedDict` o
   Pydantic model) que se pasa entre nodos del grafo. Cada nodo puede leer y
   escribir al estado. Es la version mas estructurada del patron — pero
   requiere adoptar todo el framework.

4. **Cognitive Architecture** (Sumers et al., 2023 - "Cognitive Architectures
   for Language Agents"): Proponen un framework unificado donde la working memory
   es un componente central que conecta percepcion, razonamiento y accion.

### Nuestra variante: Tool-Scoped Working Memory

Implementamos una variante especifica que combina dos niveles de memoria:

```
┌─────────────────────────────────────────────────────┐
│  Agent Run (1 pregunta del usuario)                 │
│                                                     │
│  ┌─ Iteration 1 ─────────────────────────────────┐  │
│  │  search_fhir → entries = [Conditions...]      │  │
│  │  execute_code → store['dm2'] = set(...)       │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌─ Iteration 2 ─────────────────────────────────┐  │
│  │  search_fhir → entries = [Observations...]    │  │  ← entries sobreescrito
│  │  execute_code → store['dm2'] sigue vivo!      │  │  ← store persiste
│  │               → result = store['dm2'] & obs   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  store se resetea al finalizar el run               │
└─────────────────────────────────────────────────────┘
```

| Variable | Tipo | Lifetime | Semantica | Analogia |
|----------|------|----------|-----------|----------|
| `entries` | list | Ultimo search | Cache de resultado (sobreescrito) | Registro sensorial |
| `store` | dict | Toda la ejecucion | Memoria acumulativa (agente decide que guardar) | Working memory |
| message history | list | Toda la ejecucion | Historial de pasos | Memoria episodica |

La diferencia clave con LangGraph State: nuestro `store` es **opaco** — el
framework no sabe que hay adentro, solo el agente decide que guardar. En
LangGraph, el estado es tipado y el framework puede hacer merge/reduce.
Elegimos la version opaca porque es mas simple y el agente solo necesita
guardar sets de IDs entre busquedas, no estado estructurado complejo.

---

## Decision

Agregar un **`store` dict persistente** al `ToolRegistry` que se inyecta en
`execute_code` junto con `entries`. El agente puede guardar resultados
intermedios entre busquedas sin re-querying.

### Ejemplo de uso

```python
# Iteracion 1: buscar Conditions, guardar patient IDs
search_fhir("Condition", {"code": "...", "_include": "Condition:subject"})
execute_code("store['dm2_patients'] = set(e['subject']['reference'] "
             "for e in entries if e.get('resourceType') == 'Condition')")

# Iteracion 2: buscar Observations (entries se sobreescribe, store no)
search_fhir("Observation", {"code": "...", "_include": "Observation:subject"})
execute_code("obs_patients = set(e['subject']['reference'] for e in entries); "
             "result = store['dm2_patients'] & obs_patients; "
             "print(len(result))")
```

### Cambios implementados

1. **`tools.py`**: `ToolRegistry._store: dict` inicializado en `__init__`,
   inyectado en `execute_code` como `extra_globals={"entries": ..., "store": ...}`.
2. **`_prompt.py` (AR locale)**: Guidance en "Procesamiento de datos" sobre
   `store` + patron explicito para correlaciones en "Estrategia de consulta".
3. **`EXECUTE_CODE_DEFINITION`**: Descripcion del tool actualizada mencionando
   `store` como dict persistente.
4. **3 tests nuevos**: `test_store_persists_across_calls`,
   `test_store_cross_reference_pattern`, `test_store_persists_via_registry`.

---

## Consecuencias

### Positivas
- Elimina re-busquedas: queries cross-resource pasan de 10-12 iteraciones a ~4-5.
- Reduce costo ~50-60% en preguntas de correlacion/negacion.
- Desbloquea preguntas que antes fallan por max_iterations (C05, C30).
- Zero-cost para queries simples (store queda vacio, no se usa).
- Sin cambios en `loop.py` ni en el protocolo Tracer — solo toca `ToolRegistry`.

### Negativas
- El agente debe aprender a usar `store` via prompt — no es automatico.
- Agrega una variable mas al sandbox de `execute_code`.

### Riesgos
- El agente podria no usar `store` si el prompt no es lo suficientemente claro.
  Mitigacion: la tool description tambien lo menciona, y el planner puede
  sugerir el patron en queries multi_search.
- Acumulacion de datos en `store` podria usar memoria en queries largas.
  Mitigacion: el store se resetea entre queries (cada pregunta crea un
  ToolRegistry nuevo).

---

## Alternativas consideradas

### Opcion A: Historial de entries (stack automatico)
Cada `search_fhir` pushea a un stack: `entries_history = [entries_0, entries_1, ...]`.
- Pros: No requiere accion del agente — todos los search results se acumulan.
- Contras: El agente no sabe que nombre tienen, crece sin control, inyecta datos
  irrelevantes en contexto. Rompe la analogia cognitiva: la working memory debe
  ser selectiva, no acumulativa indiscriminada (Cowan, 2001).

### Opcion B: Variables nombradas automaticas (entries_1, entries_2, ...)
Cada search crea una nueva variable con sufijo incremental.
- Pros: Automatico, sin prompt engineering.
- Contras: El agente no sabe cuantas hay ni que contiene cada una. Fragil ante
  cambios de orden. El LLM tendria que "explorar" variables disponibles.

### Opcion C: LangGraph State tipado
Migrar a LangGraph y modelar el estado como `TypedDict`.
- Pros: Patron de primera clase, merge/reduce automatico, checkpointing.
- Contras: Adoptar un framework completo para resolver un problema de 10 lineas.
  Ver ADR-002 para la discusion completa sobre frameworks vs custom.

### Opcion D: store dict explicito (ELEGIDA)
Dict opaco, el agente decide que guardar y con que clave.
- Pros: Minimo overhead (10 loc), semantica clara, el agente tiene agency sobre
  su propia working memory. Alineado con el principio de Nye et al.: el modelo
  es mejor cuando decide que anotar.
- Contras: Requiere prompt guidance.

---

## Referencias

### Papers
- Nye et al. (2021) "Show Your Work: Scratchpads for Intermediate Computation with Language Models" — arXiv:2112.00114
- Yao et al. (2022) "ReAct: Synergizing Reasoning and Acting in Language Models" — arXiv:2210.03629
- Schick et al. (2023) "Toolformer: Language Models Can Teach Themselves to Use Tools" — arXiv:2302.04761
- Park et al. (2023) "Generative Agents: Interactive Simulacra of Human Behavior" — arXiv:2304.03442
- Sumers et al. (2023) "Cognitive Architectures for Language Agents" — arXiv:2309.02427
- Cowan (2001) "The magical number 4 in short-term memory" — Behavioral and Brain Sciences

### Frameworks
- LangGraph State: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
- AutoGPT workspace: https://github.com/Significant-Gravitas/AutoGPT

### Codigo
- `packages/saludai-agent/src/saludai_agent/tools.py` — `ToolRegistry._store`
- `packages/saludai-core/src/saludai_core/locales/ar/_prompt.py` — guidance de `store`
- ADR-002: No LangChain (contexto de la decision de framework)
- ADR-009: Hybrid Query Planner (planner que clasifica preguntas)
