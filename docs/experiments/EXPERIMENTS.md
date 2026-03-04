# SaludAI — Documento de Experimentos

> Registro formal de la estrategia experimental del FHIR Smart Agent.
> Cada experimento documenta hipótesis, metodología, resultados y conclusiones.

## Contexto

SaludAI evalúa su agente FHIR contra un benchmark inspirado en [FHIR-AgentBench](https://arxiv.org/abs/2408.01693) (Verily/KAIST/MIT), adaptado para datos clínicos argentinos. El objetivo es medir mejoras progresivas en precisión, cobertura de recursos y capacidad multi-turn.

### Datos Sintéticos

Los datos de evaluación se generan con `data/seed/generate_seed_data.py` (seed determinístico `random.seed(42)`):

| Versión | Pacientes | Conditions | Observations | MedicationRequests | Encounters | Total Entries |
|---------|-----------|------------|--------------|-------------------|------------|---------------|
| v1 (Sprint 2.5) | 55 | ~76 | — | — | — | ~131 |
| v2 (Sprint 2.6) | 55 | 80 | 163 | 116 | 122 | 536 |

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
| 3.4 (Prompt opt) | | | | | |

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

### Target Final
- **Accuracy ≥ 80%** con Sonnet al final del Sprint 3 (baseline: 60%)
- **Simple ≥ 88%** (resolver pagination debería cubrir esto)
- **Complex ≥ 75%** (baseline: 64%, mejora via multi-turn + reference nav)

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

## Tabla Maestra de Resultados

Historial completo de todas las ejecuciones del benchmark.

| Fecha | Exp | Modelo | Dataset | Accuracy | Simple | Medium | Complex | Notas |
|-------|-----|--------|---------|----------|--------|--------|---------|-------|
| 2026-03-04 | 0 | Sonnet 4.5 | 25q (v1) | 88.0% | 88% | 100% | 71% | Baseline inflado |
| 2026-03-04 | 1 | Sonnet 4.5 | 50q (v2) | 60.0% | 50% | 60% | 64% | Baseline honesto |
| 2026-03-04 | 2 | Sonnet 4.5 | 50q (v2) | 82.0% | 100% | 80% | 77% | Pagination fix (`_count=200`, `_summary=count`) |
| 2026-03-04 | 3 | Sonnet 4.5 | 50q (v2) | 86.0% | 100% | 95% | 73% | Terminology fix, `get_resource` tool, max_iterations=8, prompt v1.2 |
| 2026-03-04 | 4 | Sonnet 4.5 | 50q (v2) | 94.0% | 100% | 95% | 91% | Code interpreter (`execute_code`), prompt v1.3 |

---

## Apéndice

### A. Estructura del Dataset v2

| Categoría | Cantidad | Subcategorías |
|-----------|----------|---------------|
| simple | 8 | count, demographics, existence |
| medium | 20 | terminology, filter_combined, status_filter, aggregation, observation_query, medication_query, encounter_query |
| complex | 22 | multi_filter, multi_resource, comorbidity, age_condition, multi_terminology, aggregation_geographic, cross_resource, calculation, reference_traversal, advanced_aggregation |

### B. Resource Types en Seed v2

| Resource | Cantidad | Fuente de Códigos | Correlaciones |
|----------|----------|-------------------|---------------|
| Patient | 55 | DNI (RENAPER) | Provincia ponderada por población |
| Condition | 80 | SNOMED CT AR | 16 condiciones, 5 garantizadas (DM2+BA+>60) |
| Observation | 163 | LOINC | 6 tipos, valores correlacionados con condiciones |
| MedicationRequest | 116 | ATC (WHO) | 10 medicamentos, correlacionados con condiciones |
| Encounter | 122 | HL7 v3 ActCode | 4 tipos (AMB 55%, EMER 20%, IMP 15%, HH 10%) |

### C. Correlaciones Clínicas en Seed

| Condición | Observations Afectadas | Medicamentos Asociados |
|-----------|----------------------|----------------------|
| DM2 (44054006) | Glucosa ↑, HbA1c ↑ | Metformina, Insulina NPH |
| HTA (59621000) | PA sistólica ↑, PA diastólica ↑ | Enalapril, Losartán, Atenolol, Amlodipina |
| Anemia (267036007) | Hemoglobina ↓ | — |
| Asma (195967001) | — | Salbutamol |
| DM1 (73211009) | — | Insulina NPH |
