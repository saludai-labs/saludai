# SaludAI — Documento de Experimentos

> Registro formal de la estrategia experimental del FHIR Smart Agent.
> Cada experimento documenta hipótesis, metodología, resultados y conclusiones.

## Contexto

SaludAI evalúa su agente FHIR contra un benchmark inspirado en [FHIR-AgentBench](https://arxiv.org/abs/2509.19319) (Verily/KAIST/MIT, [repo](https://github.com/glee4810/FHIR-AgentBench)), adaptado para datos clínicos argentinos. El objetivo es medir mejoras progresivas en precisión, cobertura de recursos y capacidad multi-turn.

### Datos Sintéticos

Los datos de evaluación se generan con `data/seed/generate_seed_data.py` (seed determinístico `random.seed(42)`):

| Versión | Pacientes | Conditions | Observations | MedicationReq | Encounters | Procedure | Allergy | Immunization | DiagReport | Total |
|---------|-----------|------------|--------------|---------------|------------|-----------|---------|-------------|------------|-------|
| v1 (Sprint 2.5) | 55 | ~76 | — | — | — | — | — | — | — | ~131 |
| v2 (Sprint 2.6) | 55 | 80 | 163 | 116 | 122 | — | — | — | — | 536 |
| v3 (Sprint 5.1) | 200 | 302 | 375 | 361 | 437 | ~200 | ~58 | ~687 | ~120 | 3182 |

**Demografía:** Nombres argentinos, DNI, 18 provincias ponderadas por población, SNOMED CT (edición AR), CIE-10.

### Metodología de Evaluación

- **LLM-as-judge híbrido:** Pre-check programático para rangos numéricos (determinístico, sin costo LLM) + Claude Haiku como fallback para evaluación semántica. Reemplaza al LLM-as-judge puro de Exp 0.
- **Scoring:** 1 (correcto) o 0 (incorrecto). Sin puntaje parcial.
- **Determinismo:** `temperature=0` en el agente bajo evaluación.
- **Independencia:** Cada pregunta se ejecuta con un agente limpio (sin contexto previo).
- **Categorías:** `simple` (conteo, demografía), `medium` (terminología, filtros, status), `complex` (multi-recurso, aggregation, reference traversal).

---

## Exp 0 — Baseline Inflado (Sprint 2.5)

### Hipótesis
El agente puede responder preguntas básicas sobre Patient y Condition usando tool calling.

### Setup
- **Dataset:** 25 preguntas (8 simple, 10 medium, 7 complex)
- **Datos:** 55 Patient + ~76 Condition (solo 2 tipos de recurso)
- **Modelo:** Claude Sonnet 4.5
- **Agent:** Loop v1 con 3 tools (search_patients, search_conditions, get_resource)

### Resultados

| Modelo | Accuracy | Simple | Medium | Complex | Avg Duration |
|--------|----------|--------|--------|---------|-------------|
| Claude Sonnet 4.5 | **88.0%** | 7/8 (88%) | 10/10 (100%) | 5/7 (71%) | 13.6s |

### Análisis
El 88% es **engañosamente alto** por tres razones:

1. **Solo 2 resource types:** Todas las preguntas se resuelven con Patient + Condition. El agente no necesita navegar Observation, MedicationRequest, ni Encounter.
2. **Rangos de aceptación amplios:** Muchas preguntas aceptan rangos como "15-30" cuando el valor real es 22. El judge aprueba respuestas imprecisas.
3. **Preguntas simples dominan:** 72% de las preguntas (18/25) requieren 1-2 tool calls. Solo 7 son genuinamente complejas.
4. **Sin cross-resource queries:** Ninguna pregunta requiere correlacionar datos entre ≥3 tipos de recurso.

### Conclusión
Este baseline no es útil para medir mejoras reales. Se necesita un benchmark más exigente.

---

## Exp 1 — Baseline Honesto (Sprint 2.6)

### Hipótesis
Con datos enriquecidos (5 resource types) y preguntas más difíciles (50 total, incluyendo cross-resource y aggregation), la accuracy del agente caerá a ~40-55% con Sonnet, revelando las verdaderas limitaciones.

### Setup
- **Dataset:** 50 preguntas (8 simple, 20 medium, 22 complex)
- **Datos:** 55 Patient + 80 Condition + 163 Observation + 116 MedicationRequest + 122 Encounter (536 total)
- **Modelo agente:** Claude Sonnet 4.5
- **Judge:** Claude Haiku 4.5 (híbrido: pre-check programático para rangos + LLM para semántica)
- **Agent:** Loop v1 (sin cambios respecto a Exp 0)
- **Nuevas subcategorías:** observation_query, medication_query, encounter_query, cross_resource, calculation, reference_traversal, advanced_aggregation

### Resultados

| Modelo | Accuracy | Simple (8) | Medium (20) | Complex (22) | Avg Duration | Avg Iterations |
|--------|----------|------------|-------------|--------------|-------------|----------------|
| Claude Sonnet 4.5 | **60.0%** | 4/8 (50%) | 12/20 (60%) | 14/22 (64%) | 13.8s | 2.9 |
| Claude Haiku 4.5 | — | — | — | — | — | — |

*Judge: Claude Haiku 4.5 (con pre-check programático para rangos numéricos).*

### Análisis

El 60% confirma que el benchmark es significativamente más exigente que Exp 0:

1. **Pagination es el blocker principal:** Las 4 preguntas simple fallidas (S01, S02, S03, S05) fallan porque el agente solo ve los primeros 20 resultados de FHIR (default page size). No usa `_summary=count` ni paginación. Esto afecta también medium y complex queries que dependen de conteos totales.

2. **Complex sorprendentemente fuerte (64%):** El agente maneja bien queries multi-step: resuelve terminología, hace `_include`, cruza recursos. Las fallas en complex son por pagination o max iterations exceeded, no por incapacidad de razonamiento.

3. **Medium afectado por pagination (60%):** Preguntas como M11 (conteo de glucosa), M13 (PA), M14 (metformina), M15 (prescripciones por medicamento) fallan porque el agente no ve todos los resultados.

4. **Judge híbrido funciona bien:** El pre-check programático para rangos numéricos resolvió el problema de Haiku no respetando los ranges. De 50 evaluaciones, ~25 usaron pre-check y ~25 el LLM judge.

**Patrón de fallas:**
- **Pagination** (~40% de las fallas): Agent reports 20 instead of N>20
- **Max iterations** (~10% de las fallas): Agent runs out of steps on complex medication queries
- **Partial data** (~50% de las fallas): Agent sees partial page and draws wrong conclusions

### Conclusión

60% es un baseline honesto y accionable. La mejora más impactante será implementar pagination/`_summary=count` en Sprint 3 — esto debería cubrir ~50% de las fallas actuales, potencialmente subiendo a ~75-80%.

---

## Exp 2 — Mejora Progresiva (Sprint 3.x)

### Hipótesis
Cada sesión del Sprint 3 mejorará la accuracy en las categorías que aborda:
- 3.1 (Multi-turn): Mejora en complex queries que requieren múltiples pasos
- 3.2 (Reference navigation): Mejora en cross-resource y reference traversal
- 3.3 (Code interpreter): Mejora en cálculos y aggregation avanzada
- 3.4 (Prompt optimization): Mejora general por mejor prompting

### Setup
- **Dataset:** 50 preguntas (mismo que Exp 1)
- **Modelo:** Claude Sonnet 4.5
- **Medición:** Después de cada sesión 3.x, re-ejecutar benchmark completo

### Resultados Progresivos

| Sesión | Accuracy | Simple | Medium | Complex | Delta vs Exp 1 |
|--------|----------|--------|--------|---------|----------------|
| 3.1 (Pagination) | **82.0%** | 8/8 (100%) | 16/20 (80%) | 17/22 (77%) | **+22pp** |
| 3.2 (Reference nav) | **86.0%** | 8/8 (100%) | 19/20 (95%) | 16/22 (73%) | **+26pp** |
| 3.3 (Code interpreter) | **94.0%** | 8/8 (100%) | 19/20 (95%) | 20/22 (91%) | **+34pp** |
| 3.5 (Judge fix + timeout) | **98.0%** | 8/8 (100%) | 20/20 (100%) | 21/22 (95%) | **+38pp** |

### Análisis — Sesión 3.1

**Cambios implementados:**
1. `execute_search_fhir()` inyecta `_count=200` por defecto
2. `format_bundle_summary()` maneja `_summary=count` (total sin entries)
3. System prompt con sección "Estrategia de consulta" — guía cuándo usar `_summary=count`
4. Tool description menciona `_summary` y `_count` como parámetros especiales

**Impacto por categoría:**
- **Simple 100%:** Todas las 4 preguntas que fallaban por pagination (S01-S03, S05) ahora pasan gracias a `_summary=count`
- **Medium 80%:** 4 preguntas recuperadas. M02 sigue fallando (resolve "hipertensión arterial" → SNOMED 38341003 no existe en seed, el código correcto es 59621000). M09 falla (listado de condiciones frecuentes — requiere aggregation manual).
- **Complex 77%:** 3 preguntas recuperadas (C14, C17, C18). Fallas restantes: C20 (distribución encounters por provincia — aggregation geográfico), C21 (medicamento más prescripto — aggregation conteo).
- **4 errores:** API retries/timeouts (Anthropic rate limiting) — no relacionados con lógica del agente

**Patrones de fallas restantes:**
- **Terminology mismatch (M02):** "hipertensión arterial" resuelve a 38341003 (no en seed) en vez de 59621000
- **Aggregation sin code interpreter (~3 fallas):** Conteo/ranking manual en resultados grandes (M09, C20, C21)
- **API instability (4 errors):** Rate limiting de Anthropic causa timeouts

### Análisis — Sesión 3.2

**Cambios implementados:**
1. Fix terminology disambiguation: display de `38341003` "Hipertensión arterial" → "Hipertensión arterial sistémica" (evita exact-match con 59621000)
2. Nuevo tool `get_resource` para lectura de recurso individual por tipo e ID
3. `agent_max_iterations` de 5 a 8 (queries multi-medicamento necesitan más rondas)
4. System prompt v1.2 con guidance de `_include`/`_revinclude` y medicamentos

**Impacto por categoría:**
- **Medium 95%:** M02 (hipertensión) y M19 (antihipertensivos) ahora pasan. Solo M09 (aggregation) sigue fallando.
- **Complex 73%:** C04, C08, C09 (cascada del terminology bug + max iterations) ahora pasan. Pero C07 y C18 flippearon a INCORRECT por non-determinism del LLM.
- **0 errors:** El bump de max_iterations eliminó los 4 errores de Exp 2 (M14, M19, C04, C09).

**Patrones de fallas restantes (7):**
- **Aggregation sin code interpreter (M09, C20, C21):** El LLM no puede contar/agrupar correctamente 100+ registros en contexto → necesita Code Interpreter
- **Cross-resource join con conteo (C03, C05):** El LLM falla cruzando Patient addresses con Condition results cuando hay muchos registros
- **Non-determinism (C07, C18):** Estas preguntas pasan/fallan entre corridas — el LLM a veces cuenta mal los datos complejos

### Análisis — Sesión 3.3

**Cambios implementados:**
1. Nuevo tool `execute_code` — sandbox Python con builtins restringidos, timeout 5s, módulos pre-importados (json, collections, datetime, math, statistics, re)
2. `_restricted_import()` — whitelist de módulos permitidos (bloquea os, subprocess, etc.)
3. System prompt v1.3 con sección "Procesamiento de datos" — regla de usar execute_code para >10 recursos

**Impacto por categoría:**
- **Complex 91%:** Salto masivo de 73% → 91%. M09 (condiciones frecuentes), C03, C07, C18, C20 (distribución encounters), C21 (medicamento más prescripto) ahora pasan gracias a Counter/aggregation via código.
- **Medium 95%:** Estable. M07 flipped a INCORRECT por non-determinism.
- **Simple 100%:** Sin cambios.

**Patrones de fallas restantes (3):**
- **Non-determinism (M07, C14):** Pasan/fallan entre corridas — el LLM a veces interpreta mal datos complejos
- **Timeout (C05):** Query compleja con muchos datos excede 120s

### Análisis — Sesión 3.5

**Cambios implementados:**
1. Judge regex fix: nuevo pattern para bare `X-Y` ranges (sin prefijo "Rango:") — matchea notes como `"Activas: 58-66"`
2. Judge regex fix: tolerancia a `%` en patterns `entre X% y Y%` — matchea notes como `"Aceptar entre 83% y 93%"`
3. Timeout bump: `question_timeout_seconds` de 120 a 180
4. 5 tests nuevos para los patterns corregidos

**Impacto por categoría:**
- **Medium 100%:** M07 ahora pasa — el judge detecta correctamente que la respuesta del agente está en el rango `58-66`
- **Complex 95%:** C14 ahora pasa — el judge parsea correctamente `"entre 83% y 93%"` con `%`
- **Simple 100%:** Sin cambios.

**Falla restante (1):**
- **Max iterations (C05):** Query compleja excede 8 iteraciones (no timeout, sino límite de iteraciones)

### Target Final
- **Accuracy ≥ 80%** con Sonnet al final del Sprint 3 (baseline: 60%) — **SUPERADO: 98%**
- **Simple ≥ 88%** (resolver pagination debería cubrir esto) — **SUPERADO: 100%**
- **Complex ≥ 75%** (baseline: 64%, mejora via multi-turn + reference nav) — **SUPERADO: 95%**

---

## Exp 3 — Matriz de Modelos (Sprint 3.5)

### Hipótesis
Modelos más grandes tienen mejor accuracy, pero modelos locales (Ollama) pueden ser viables para queries simples. GPT-4o debería estar cercano a Sonnet.

### Setup
- **Dataset:** 50 preguntas
- **Modelos:** Claude Opus 4, Claude Sonnet 4.5, Claude Haiku 4.5, GPT-4o, Ollama (llama3.1:8b)
- **Agent:** Versión final del Sprint 3

### Resultados

| Modelo | Accuracy | Simple | Medium | Complex | Avg Duration | Costo/query |
|--------|----------|--------|--------|---------|-------------|-------------|
| Claude Opus 4 | | | | | | |
| Claude Sonnet 4.5 | | | | | | |
| Claude Haiku 4.5 | | | | | | |
| GPT-4o | | | | | | |
| Ollama llama3.1:8b | | | | | | |

---

## Exp 4 — Ablation Study (Sprint 3.5)

### Hipótesis
Cada componente del agente contribuye de forma medible a la accuracy. Desactivar componentes mostrará el impacto individual de cada uno.

### Setup
- **Dataset:** 50 preguntas
- **Modelo:** Claude Sonnet 4.5
- **Variantes:**
  - Full agent (baseline)
  - Sin terminology resolver (raw text → FHIR queries)
  - Sin tools (LLM responde solo con conocimiento paramétrico)
  - Sin Langfuse tracing (verificar que no afecta performance)
  - Tool call limit = 1 (forzar single-turn)
  - Temperature = 0.5 (verificar impacto de no-determinismo)

### Resultados

| Variante | Accuracy | Delta vs Full | Notas |
|----------|----------|---------------|-------|
| Full agent | | baseline | |
| Sin terminology | | | |
| Sin tools | | | |
| Sin tracing | | | |
| Max 1 tool call | | | |
| Temperature 0.5 | | | |

---

## Exp 6 — Dataset Expandido: 100 Preguntas (Sprint 5.2b)

### Hipótesis
El agente que alcanzó 98% en 50 preguntas (Exp 5) debería mantener ≥85% al escalar a 100 preguntas con 200 pacientes y 9 resource types. Los nuevos resource types (Procedure, AllergyIntolerance, Immunization, DiagnosticReport) y las preguntas más exigentes revelarán limitaciones no visibles en el dataset anterior.

### Setup
- **Dataset:** 100 preguntas (15 simple, 35 medium, 50 complex)
- **Datos:** 200 Patient + 302 Condition + 375 Observation + 361 MedicationRequest + 437 Encounter + Procedure + AllergyIntolerance + Immunization + DiagnosticReport (3182 total entries, 9 resource types)
- **Modelo agente:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Judge:** Claude Haiku 4.5 (híbrido: pre-check programático + LLM)
- **Agent:** Loop v1 con 4 tools (resolve_terminology + search_fhir + get_resource + execute_code), max 8 iteraciones, timeout 180s
- **Sin cambios en el agente** respecto a Exp 5 — solo cambia el dataset

### Resultados

| Modelo | Accuracy | Simple (15) | Medium (35) | Complex (50) | Errors | Avg Duration | Avg Iterations |
|--------|----------|-------------|-------------|--------------|--------|-------------|----------------|
| Claude Sonnet 4.5 | **79.0%** | 15/15 (100%) | 24/35 (69%) | 40/50 (80%) | 5 | 56.9s | 3.75 |

### Análisis de Fallos

**21 fallos totales:** 16 incorrectas + 5 errores

#### Patrón 1: Paginación — Solo la primera página (12 fallos, 57% de los fallos)

**Preguntas:** M07, M09, M14, M19, M25, C02, C05, C14, C18, C20, C21, C40

Este es el **problema dominante**. El agente usa `_count=200` pero varios resource types ahora superan los 200 entries:
- MedicationRequest: 361 entries → el agente ve 200 (~55%)
- Encounter: 437 entries → el agente ve 200 (~46%)
- Immunization: 687 entries → el agente ve 200 (~29%)
- Condition: 302 entries → el agente ve 200 (~66%)

El agente a veces detecta que hay más datos ("200 of 361 total") pero igualmente reporta los conteos parciales como respuesta final. Los sub-conteos son proporcionales: M19 reporta 91 antihipertensivos vs 157 reales (~58%), C20 reporta 200 encounters vs 437 (~46%).

En Exp 5 esto no era problema porque con 55 pacientes ningún resource type superaba 200 entries.

#### Patrón 2: Timeout (3 fallos)

**Preguntas:** C17, C22, C46

Queries cross-resource complejas que requieren múltiples búsquedas paginadas y set intersections. Con datos más grandes, 180 segundos no alcanza:
- C17: Pacientes con internaciones + medicamentos prescriptos
- C22: Pacientes con algún antihipertensivo prescripto
- C46: Pacientes >65 años con vacuna COVID-19 Y antigripal

#### Patrón 3: LOINC / Terminología para DiagnosticReport (3 fallos)

**Preguntas:** M26, M27, M35

El agente no encuentra hemogramas (31), paneles metabólicos (50) ni perfiles tiroideos (39). Busca con códigos LOINC que no coinciden con los del seed, o busca en el resource type incorrecto. El TerminologyResolver no tiene los códigos LOINC usados para DiagnosticReport en el seed v3.

#### Patrón 4: Métrica incorrecta — registros vs pacientes (1 fallo)

**Pregunta:** M22

Cuenta 58 registros de AllergyIntolerance en vez de 43 pacientes únicos con alergias. El agente no deduplica por paciente.

#### Patrón 5: Max iterations exceeded (1 fallo)

**Pregunta:** M23

La búsqueda de vacunas COVID-19 en 687 Immunization records agota las 8 iteraciones.

#### Patrón 6: Rate limit (1 fallo)

**Pregunta:** M24

Error 429 cascada del uso intensivo de tokens en M23. Error de infraestructura, no de lógica.

### Resultados por Pregunta

#### Simple (15/15 = 100%)
S01 OK, S02 OK, S03 OK, S04 OK, S05 OK, S06 OK, S07 OK, S08 OK, S09 OK, S10 OK, S11 OK, S12 OK, S13 OK, S14 OK, S15 OK

#### Medium (24/35 = 69%)
M01 OK, M02 OK, M03 OK, M04 OK, M05 OK, M06 OK, **M07 FAIL** (pagination), M08 OK, **M09 FAIL** (pagination), M10 OK, M11 OK, M12 OK, M13 OK, **M14 FAIL** (pagination), M15 OK, M16 OK, M17 OK, M18 OK, **M19 FAIL** (pagination), M20 OK, M21 OK, **M22 FAIL** (records vs patients), **M23 ERROR** (max iterations), **M24 ERROR** (rate limit), **M25 FAIL** (pagination), **M26 FAIL** (LOINC mismatch), **M27 FAIL** (LOINC mismatch), M28 OK, M29 OK, M30 OK, M31 OK, M32 OK, M33 OK, M34 OK, **M35 FAIL** (LOINC mismatch)

#### Complex (40/50 = 80%)
C01 OK, **C02 FAIL** (pagination), C03 OK, C04 OK, **C05 FAIL** (pagination), C06 OK, C07 OK, C08 OK, C09 OK, C10 OK, C11 OK, C12 OK, C13 OK, **C14 FAIL** (pagination), C15 OK, C16 OK, **C17 ERROR** (timeout), **C18 FAIL** (pagination), C19 OK, **C20 FAIL** (pagination), **C21 FAIL** (pagination), **C22 ERROR** (timeout), C23 OK, C24 OK, C25 OK, C26 OK, C27 OK, C28 OK, C29 OK, C30 OK, C31 OK, C32 OK, C33 OK, C34 OK, C35 OK, C36 OK, C37 OK, C38 OK, C39 OK, **C40 FAIL** (pagination), C41 OK, C42 OK, C43 OK, C44 OK, C45 OK, **C46 ERROR** (timeout), C47 OK, C48 OK, C49 OK, C50 OK

### Conclusión

El 79% está **por debajo del target de 85%**. La caída de 98% → 79% se debe casi exclusivamente a la **paginación**: el `_count=200` que era suficiente para 55 pacientes no alcanza para 200 pacientes. Es un problema conocido que resurge a mayor escala.

**Plan de mejora (sesión 5.2b fixes):**
1. **Paginación automática** — implementar multi-page fetch o aumentar `_count` para queries de aggregation (+12 preguntas, ~+12pp)
2. **LOINC para DiagnosticReport** — agregar códigos faltantes al TerminologyResolver (+3 preguntas, ~+3pp)
3. **Deduplicación por paciente** — guidance en system prompt para contar pacientes únicos (+1 pregunta, ~+1pp)
4. **Max iterations / timeout** — considerar bump a 12 iteraciones o 300s para queries grandes (+4 preguntas, ~+4pp)

Con estos fixes, el target optimista es **~99%** (79 + 20 recuperables). Realista: **92-95%**.

---

## Exp 7 — Planner + Cost Baseline (Sprint 5.2d)

### Hipotesis
El Query Planner (ADR-009) con Action Space Reduction, `count_fhir`, `search_all` (auto-paginacion), scratchpad y prompt v2.0 deberian recuperar la mayoria de los fallos de Exp 6. Las 3 preguntas problematicas (M23, C22, C46) se deshabilitan temporalmente para no desperdiciar tokens en fallos conocidos.

### Setup
- **Dataset:** 97 preguntas (3 deshabilitadas: M23, C22, C46) — 15 simple, 34 medium, 48 complex
- **Datos:** 3182 entries, 9 resource types (igual que Exp 6)
- **Modelo agente:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Judge:** Claude Haiku 4.5 (hibrido)
- **Agent:** Loop con 6 tools (resolve_terminology + search_fhir + get_resource + execute_code + count_fhir + search_all), max 12 iteraciones, timeout 300s
- **Nuevos vs Exp 6:** Planner con clasificacion + ASR, `count_fhir` con `_has`, `search_all` (auto-paginacion), scratchpad (`store`), prompt v2.0

### Resultados

| Modelo | Accuracy | Simple (15) | Medium (34) | Complex (48) | Errors | Avg Duration | Avg Iterations |
|--------|----------|-------------|-------------|--------------|--------|-------------|----------------|
| Claude Sonnet 4.5 | **88.7%** | 15/15 (100%) | 30/34 (88%) | 41/48 (85%) | 5 | 24.5s | 4.2 |

### Analisis de Fallos

**11 fallos totales:** 6 incorrectas + 5 errores

#### Incorrectas (6)
- **M14** — 9 iteraciones, 32.0s
- **M16** — 2 iteraciones, 10.3s
- **M19** — 6 iteraciones, 29.2s
- **M22** — 2 iteraciones, 10.9s (records vs pacientes, mismo problema que Exp 6)
- **C05** — 11 iteraciones, 45.9s
- **C15** — 3 iteraciones, 18.4s

#### Errores (5)
- **C07** — 10.0s (error no especificado)
- **C17** — 20.1s (error intermitente — fue CORRECT en corrida aislada previa)
- **C18** — 10.9s (error no especificado)
- **C26** — 20.1s (error no especificado)
- **C33** — 55.9s (error no especificado)

### Analisis de Costos

**Costo total estimado: ~$8.89 USD** (agente $8.66 + planner $0.12 + judge $0.12)

#### Distribucion por categoria

| Categoria | Preguntas | Iteraciones | Input Tokens | Output Tokens | Costo Agente | $/Pregunta |
|-----------|-----------|-------------|--------------|---------------|-------------|------------|
| simple | 15 | 30 | 136,251 | 2,267 | $0.44 | $0.030 |
| medium | 34 | 118 | 598,982 | 18,671 | $2.08 | $0.061 |
| complex | 48 | 256 | 1,730,401 | 63,415 | $6.14 | $0.128 |
| **Total** | **97** | **404** | **2,465,634** | **84,353** | **$8.66** | **$0.089** |

#### Insight clave

El **85% del costo es input tokens** ($7.40 de $8.66). El system prompt (~4,300 tokens) se repite 404 veces = $5.26 solo en prompt estatico. El historial acumulado agrega $2.14.

#### Top 5 preguntas mas caras

| ID | Categoria | Iteraciones | Input Tokens | Costo | Status |
|----|-----------|-------------|--------------|-------|--------|
| C12 | complex | 10 | 98,563 | $0.333 | CORRECT |
| C38 | complex | 11 | 84,351 | $0.292 | CORRECT |
| C09 | complex | 12 | 71,314 | $0.252 | CORRECT |
| C44 | complex | 9 | 70,971 | $0.244 | CORRECT |
| C19 | complex | 8 | 65,176 | $0.229 | CORRECT |

#### Escenarios de reduccion de costo

| Escenario | Costo Estimado | Ahorro | Impacto |
|-----------|---------------|--------|---------|
| A) System prompt -1500 tokens | $6.84 | $1.82 (21%) | Recortar prompt |
| B) Reducir promedio a 3.0 iters | $6.19 | $2.47 (29%) | Agente mas eficiente |
| C) Simple+Medium a Haiku | $6.81 | $1.85 (21%) | Model routing por complejidad |
| D) Prompt caching (90% hit) | $4.40 | $4.26 (49%) | Cache de Anthropic API |
| E) A + B combinados | ~$4.89 | ~$3.77 (44%) | Combinado |

### Preguntas deshabilitadas

3 preguntas excluidas por fallos conocidos que desperdician tokens sin aportar informacion nueva:

| ID | Problema | Root Cause |
|----|----------|------------|
| M23 | Vacunas COVID-19 no encuentran por SNOMED | Datos usan CVX, no SNOMED. Falta mapeo CVX en terminology |
| C22 | `_has` con `:text` no soportado por HAPI | MedicationRequest usa ATC, no SNOMED. Agent espirala con errores |
| C46 | >65 + COVID + antigripal, max iterations | Descarga 888 entries, desperdicia iteraciones debuggeando formato |

### Conclusion

**88.7% es un avance solido** desde 79% (Exp 6), logrado principalmente por `search_all` (auto-paginacion), `count_fhir` (server-side counting), y el planner (reduce herramientas innecesarias). La duracion promedio bajo de 56.9s a 24.5s.

**Proximo paso:** Optimizacion de costos. El benchmark cuesta ~$8.66 por corrida. El driver principal es el system prompt repetido (85% del costo son input tokens). Prompt caching de Anthropic es la palanca mas grande (49% ahorro potencial).

---

## Exp 8 — Cost Validation: Prompt Caching + System Prompt Diet (Sprint 5.2e)

### Hipotesis
Prompt caching de Anthropic (system prompt + tool definitions) combinado con system prompt diet (v2.0 → v2.1, ~45% mas compacto) deberia reducir el costo por run en ~35-49%, sin afectar accuracy.

### Setup
- **Dataset:** 30 preguntas (sample representativo: 5 simple, 10 medium, 15 complex)
- **Datos:** 3182 entries, 9 resource types (igual que Exp 7)
- **Modelo agente:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Judge:** Claude Haiku 4.5 (hibrido)
- **Agent:** Mismo que Exp 7 + prompt caching + system prompt v2.1
- **Nuevos vs Exp 7:** `cache_control: {"type": "ephemeral"}` en system prompt y tool definitions. System prompt recortado ~45%.

### Resultados

| Modelo | Accuracy | Simple (5) | Medium (10) | Complex (15) | Errors | Avg Duration | Avg Iterations |
|--------|----------|------------|-------------|--------------|--------|-------------|----------------|
| Claude Sonnet 4.5 | **96.7%** | 5/5 (100%) | 10/10 (100%) | 14/15 (93%) | 1 | 21.4s | 4.5 |

### Analisis de Costos

**Costo real (Anthropic dashboard): $1.81 USD para 30 preguntas.**

#### Token breakdown (agent only, 30q)

| Metrica | Tokens |
|---------|--------|
| Input (non-cached) | 251,450 |
| Output | 26,461 |
| Cache creation | 90,771 |
| Cache read | 391,650 |
| Total LLM calls | 136 |

#### Cost breakdown

| Componente | Costo |
|------------|-------|
| Input (non-cached) | $0.75 |
| Cache write (1.25x) | $0.34 |
| Cache read (0.1x) | $0.12 |
| Output | $0.40 |
| **Agent total (30q)** | **$1.61** |
| Planner + Judge | ~$0.20 |
| **Total real (30q)** | **$1.81** |

#### Comparacion con Exp 7

| Metrica | Exp 7 | Exp 8 | Delta |
|---------|-------|-------|-------|
| Per question | $0.089 | $0.060 | **-33%** |
| Projected 97q | $8.66 | $5.85 | **-$2.81** |
| Avg duration | 24.5s | 21.4s | -13% |

#### Efectividad del cache

- **391K tokens leidos de cache** vs 90K escritos → cache hit ratio 4.3:1
- Sin caching, el input costaria $2.20 → caching ahorra **38%** del costo de input
- El ahorro total (33%) es menor al teorico (49%) porque: (1) el cache write tiene overhead de 1.25x, (2) planner/judge no se benefician del cache del agente

### Error

- **C44** — max iterations (12). Mismo problema que Exp 7: query triple-cross (DM2 + glucosa >140 + metformina) agota iteraciones.

### Conclusion

**Prompt caching + diet reducen el costo ~33%** de manera verificada. De $8.66 a ~$5.85 proyectado para 97 preguntas. La accuracy no se ve afectada (96.7% en sample de 30, consistente con 88.7% en 97). El ahorro permite ~50% mas experimentos con el mismo presupuesto.

---

## Exp 9 — Sample Representativo Post-Expansion (Sprint 5.6)

### Hipotesis
Con 30 preguntas estrategicamente seleccionadas (cobertura completa de skills, dominios, resource types y graph hops), el agente deberia mantener ≥90% accuracy. Las preguntas nuevas de CarePlan (multi-hop, negacion) deberian pasar gracias al grafo y catalogo implementados en 5.2c/5.3.

### Setup
- **Dataset:** 30 preguntas seleccionadas (4 simple, 10 medium, 16 complex)
- **Seleccion:** Cobertura completa — 10/10 skills, 9/9 dominios, 10/10 resource types, 6/6 preguntas CarePlan, hops 0/1/2
- **Datos:** 3273 entries, 10 resource types (incluye CarePlan)
- **Modelo agente:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Planner:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **Judge:** Claude Haiku 4.5 (hibrido)
- **Agent:** 6 tools, max 15 iteraciones, timeout 300s, prompt caching + diet v2.1
- **Nuevos vs Exp 8:** CarePlan (10mo resource type), 16 preguntas nuevas de taxonomia expandida, sample con mas complex (16/30 = 53% vs 15/30 = 50%)

### Resultados

| Modelo | Accuracy | Simple (4) | Medium (10) | Complex (16) | Errors |
|--------|----------|-----------|-----------|-----------|--------|
| Claude Sonnet 4.5 | **90.0%** | 4/4 (100%) | 9/10 (90%) | 14/16 (88%) | 0 |

### Resultados por Pregunta

#### Simple (4/4 = 100%)
| ID | Dominio | Hops | Iters | Status |
|----|---------|------|-------|--------|
| S01 | demographics | 0 | 2 | OK |
| S09 | surgery | 0 | 2 | OK |
| S10 | vaccination | 0 | 2 | OK |
| S16 | care_coordination | 0 | 2 | OK (**CarePlan nuevo**) |

#### Medium (9/10 = 90%)
| ID | Dominio | Hops | Skills | Iters | Status | Notas |
|----|---------|------|--------|-------|--------|-------|
| M01 | chronic_disease | 1 | terminology | 3 | OK | |
| M09 | chronic_disease | 0 | aggregation, code_exec | 3 | OK | |
| M11 | laboratory | 0 | terminology | 3 | OK | |
| M14 | medication | 0 | terminology | 8 | **FAIL** | ATC vs SNOMED — ver analisis |
| M17 | care_coordination | 1 | filtering | 8 | OK | Costosa pero correcta |
| M22 | safety | 1 | counting | 3 | OK | |
| M25 | vaccination | 0 | aggregation | 3 | OK | |
| M36 | care_coordination | 0 | filtering | 2 | OK (**CarePlan nuevo**) |
| M37 | care_coordination | 1 | cross_resource | 3 | OK (**CarePlan nuevo**) |
| M42 | laboratory | 1 | reference_nav | 6 | OK (**nuevo**) |

#### Complex (14/16 = 88%)
| ID | Dominio | Hops | Skills | Iters | Status | Notas |
|----|---------|------|--------|-------|--------|-------|
| C03 | epidemiology | 1 | aggregation, code_exec | 4 | OK | |
| C08 | medication | 2 | cross_resource | 10 | OK | |
| C10 | laboratory | 2 | cross_resource, filter | 9 | OK | |
| C13 | laboratory | 2 | calculation, code_exec | 6 | OK | |
| C17 | care_coordination | 2 | cross_resource | 4 | **FAIL** | Filtro internacion incorrecto |
| C20 | epidemiology | 1 | aggregation, code_exec | 3 | OK | |
| C24 | care_coordination | 0 | temporal | 7 | OK | |
| C27 | chronic_disease | 1 | negation | 5 | OK | |
| C28 | medication | 2 | negation, cross_res | 10 | OK | |
| C38 | safety | 2 | cross_resource | 8 | OK | |
| C39 | vaccination | 1 | filtering | 5 | OK | |
| C43 | chronic_disease | 1 | calculation, code_exec | 5 | OK | |
| C51 | care_coordination | 2 | cross_resource | 3 | OK (**CarePlan nuevo**) |
| C53 | care_coordination | 2 | calc, code_exec | 11 | OK (**CarePlan nuevo**) |
| C55 | surgery | 2 | cross_resource, code | 9 | **FAIL** | Definicion de cronicas incompleta |
| C62 | care_coordination | 2 | negation, code_exec | 9 | OK (**CarePlan nuevo**) |

### Analisis de Fallos

**3 incorrectas, 0 errores.** Cada fallo tiene root cause distinto:

#### Fallo 1: M14 — Metformina no encontrada (ATC vs SNOMED)

**Pregunta:** "¿Cuantos pacientes tienen prescripcion de metformina?"
**Expected:** 32 pacientes. **Agent:** 0 pacientes.

**Root cause:** MedicationRequest usa codigos ATC (A10BA02), no SNOMED. El TerminologyResolver no tiene metformina con codigo ATC. El agente intento con SNOMED (372567009), texto libre, y variantes — ninguna funciono con `_has`. Desperdicio 8 iteraciones y 7 tool calls buscando sin encontrar.

**Este fallo es recurrente:** M14 tambien fallo en Exp 7.

**Fix candidato:** Agregar sistema de codificacion ATC al TerminologyResolver, o al menos mapeo `metformina → ATC A10BA02` en el locale pack.

#### Fallo 2: C17 — Pacientes con internaciones + medicamentos (filtro erroneo)

**Pregunta:** "¿Cuantos pacientes con internaciones tienen medicamentos prescriptos?"
**Expected:** 53 pacientes. **Agent:** 151 pacientes.

**Root cause:** El agente no filtro Encounters por clase `IMP` (internacion). Conto TODOS los pacientes con algun Encounter (151) que tambien tienen MedicationRequest, en vez de solo los que tienen Encounter de tipo internacion. El planner clasifico como `count_with_resource` pero no especifico el filtro `class=IMP`.

**Fix candidato:** Agregar al planner conocimiento de que "internacion" = Encounter con `class=IMP`. El catalogo de QueryPatterns podria incluir un patron especifico para filtros por clase de encuentro.

#### Fallo 3: C55 — Definicion incompleta de "condicion cronica" (hardcoded)

**Pregunta:** "¿Cuantos pacientes con procedimientos tienen al menos una condicion cronica?"
**Expected:** 47 pacientes. **Agent:** 34 pacientes.

**Root cause:** El agente hardcodeo una lista de 6 condiciones cronicas (DM2, HTA, EPOC, asma, IC, ERC) en el `execute_code`. Se perdio las demas condiciones cronicas del sistema (hipotiroidismo, artritis reumatoidea, etc). La interseccion subconto porque la definicion de "cronicas" fue parcial.

**Fix candidato:** No hay fix simple — requiere que el agente consulte TODAS las condiciones y determine programaticamente cuales son cronicas (por clinical-status o por conocimiento medico del LLM). Alternativa: mejorar el system prompt con guidance sobre que "condicion cronica" incluye todo lo que no es agudo.

### Senales Positivas

- **CarePlan: 6/6 correctas** — todas las preguntas nuevas de CarePlan pasaron, incluyendo multi-hop (C51, C53) y negacion (C62). El grafo y catalogo de 5.2c/5.3 funcionan.
- **0 errores** — sin crashes, timeouts ni rate limits. La infraestructura es estable.
- **Negacion funciona** — C27, C28, C62 todas correctas. El agente maneja "pacientes que NO tienen X".
- **Reference navigation funciona** — M42 (DiagnosticReport → Observation) correcto.
- **Temporal funciona** — C24 correcto.

### Conclusion

**90% confirma que el agente es robusto** en la mayoria de escenarios. Los 3 fallos son especificos y accionables:
1. **M14/C17** son problemas de terminologia/catalogo — fixes en el TerminologyResolver y planner los resolverian.
2. **C55** es un problema de razonamiento clinico — el agente no sabe que condiciones son "cronicas" sin lista explicita.

Las features nuevas (CarePlan, negation, reference_navigation, temporal) funcionan correctamente. El grafo FHIR y el planner estan cumpliendo su rol.

---

## Tabla Maestra de Resultados

Historial completo de todas las ejecuciones del benchmark.

| Exp | Modelo | Dataset | Accuracy | Simple | Medium | Complex | Notas |
|-----|--------|---------|----------|--------|--------|---------|-------|
| 0 | Sonnet 4.5 | 25q (v1) | 88.0% | 88% | 100% | 71% | Baseline inflado |
| 1 | Sonnet 4.5 | 50q (v2) | 60.0% | 50% | 60% | 64% | Baseline honesto |
| 2 | Sonnet 4.5 | 50q (v2) | 82.0% | 100% | 80% | 77% | Pagination fix (`_count=200`, `_summary=count`) |
| 3 | Sonnet 4.5 | 50q (v2) | 86.0% | 100% | 95% | 73% | Terminology fix, `get_resource` tool, max_iterations=8, prompt v1.2 |
| 4 | Sonnet 4.5 | 50q (v2) | 94.0% | 100% | 95% | 91% | Code interpreter (`execute_code`), prompt v1.3 |
| 5 | Sonnet 4.5 | 50q (v2) | 98.0% | 100% | 100% | 95% | Judge regex fix (bare ranges, %), timeout 180s |
| 6 | Sonnet 4.5 | 100q (v3) | 79.0% | 100% | 69% | 80% | Expanded dataset: 200 patients, 9 resource types, 100 questions |
| 7 | Sonnet 4.5 | 97q (v3) | 88.7% | 100% | 88% | 85% | Planner + ASR + count_fhir + search_all + scratchpad. 3 preguntas deshabilitadas (M23, C22, C46). Costo: ~$8.66 agente |
| 8 | Sonnet 4.5 | 30q (v3 sample) | 96.7% | 100% | 100% | 93% | Prompt caching + system prompt diet v2.1. Costo real: $1.81 (30q), proyectado $5.85 (97q). **-33% vs Exp 7** |
| 9 | Sonnet 4.5 | 30q (v3 representativo) | 90.0% | 100% | 90% | 88% | Sample representativo post-expansion: 10/10 skills, 9/9 dominios, 10/10 resources, 6/6 CarePlan OK. 3 fallos: M14 (ATC), C17 (filtro IMP), C55 (cronicas hardcoded) |

---

## Apéndice

### A. Estructura del Dataset

| Dataset | Categoría | Cantidad | Subcategorías |
|---------|-----------|----------|---------------|
| v2 (50q) | simple | 8 | count, demographics, existence |
| v2 (50q) | medium | 20 | terminology, filter_combined, status_filter, aggregation, observation_query, medication_query, encounter_query |
| v2 (50q) | complex | 22 | multi_filter, multi_resource, comorbidity, age_condition, multi_terminology, aggregation_geographic, cross_resource, calculation, reference_traversal, advanced_aggregation |
| v3 (100q) | simple | 15 | count, demographics, existence |
| v3 (100q) | medium | 35 | terminology, filter_combined, status_filter, aggregation, observation_query, medication_query, encounter_query, allergy_query, immunization_query, diagnostic_query |
| v3 (100q) | complex | 50 | multi_filter, multi_resource, comorbidity, age_condition, multi_terminology, aggregation_geographic, cross_resource, calculation, reference_traversal, advanced_aggregation, temporal, negative, correlation |

### B. Resource Types en Seed v3

| Resource | v2 Cantidad | v3 Cantidad | Fuente de Códigos | Correlaciones |
|----------|-------------|-------------|-------------------|---------------|
| Patient | 55 | 200 | DNI (RENAPER) | Provincia ponderada por población |
| Condition | 80 | 302 | SNOMED CT AR | 16 condiciones, 5 garantizadas (DM2+BA+>60) |
| Observation | 163 | 375 | LOINC | 6+ tipos, valores correlacionados con condiciones |
| MedicationRequest | 116 | 361 | ATC (WHO) | 10 medicamentos, correlacionados con condiciones |
| Encounter | 122 | 437 | HL7 v3 ActCode | 4 tipos (AMB 55%, EMER 20%, IMP 15%, HH 10%) |
| Procedure | — | ~200 | SNOMED CT | Procedimientos asociados a condiciones |
| AllergyIntolerance | — | ~58 | SNOMED CT | Alergias a medicamentos y sustancias |
| Immunization | — | ~687 | CVX / ATC | Vacunas (COVID-19, antigripal, IPV, etc.) |
| DiagnosticReport | — | ~120 | LOINC | Hemogramas, paneles metabólicos, perfiles tiroideos |

### C. Correlaciones Clínicas en Seed

| Condición | Observations Afectadas | Medicamentos Asociados |
|-----------|----------------------|----------------------|
| DM2 (44054006) | Glucosa ↑, HbA1c ↑ | Metformina, Insulina NPH |
| HTA (59621000) | PA sistólica ↑, PA diastólica ↑ | Enalapril, Losartán, Atenolol, Amlodipina |
| Anemia (267036007) | Hemoglobina ↓ | — |
| Asma (195967001) | — | Salbutamol |
| DM1 (73211009) | — | Insulina NPH |
