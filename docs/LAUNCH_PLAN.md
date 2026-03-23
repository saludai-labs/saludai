# SaludAI — Plan de Lanzamiento

> Referencia operativa para Sprint 6. Criterio rector: **cada hora invertida maximiza impresión en quien lo ve.**

## Contexto

El Módulo 1 está ~95% completo técnicamente (93.3% accuracy, 661 tests, 94% coverage, 10 ADRs).
Lo que falta no es código — es **presentación, narrativa y distribución**.

## Principio de priorización

| Lo que YA impresiona (pero nadie ve) | Lo que la gente VE en 30 segundos |
|---------------------------------------|-----------------------------------|
| 10 ADRs, 661 tests, 94% coverage | README con tabla comparativa de LLMs |
| Experiment docs, lessons.md | GIF/video del agente resolviendo algo |
| Hybrid Query Planner, locale packs | La curva "60% → 93%" como imagen |
| Working memory, action space reduction | Cuántos resources, preguntas, modelos |

## Qué NO hacer (decisiones de corte)

- **No agregar resource types.** 10 es sólido. 14 no cambia la percepción. Nadie va a comparar.
- **No fixear C17/C62.** 93.3% vende. 95% no cambia nada en la narrativa.
- **No hacer benchmark analysis CLI (5.7).** Tooling interno, invisible.
- **No full run 119q.** Las 30q representativas bastan por modelo.
- **No empezar Módulo 2.** Primero validar tracción con Módulo 1.

## Sesiones

### Sesión 6.1 — Multi-LLM Benchmark

**Objetivo:** Producir LA TABLA — el asset más compartible del proyecto.

**Modelos a evaluar (30q representativas cada uno):**

| Modelo | Provider | Costo estimado |
|--------|----------|----------------|
| Claude Sonnet 4.5 | Anthropic | Ya tenemos (Exp 10) |
| GPT-4o | OpenAI | ~$2-3 |
| Claude Haiku 4.5 | Anthropic | ~$0.50 |
| Llama 3.3 70B | Ollama (local) | $0 |

**Output esperado:**
```
| Model              | Accuracy | Cost/query | Avg latency |
|--------------------|----------|------------|-------------|
| Claude Sonnet 4.5  | 93.3%    | $0.060     | 24s         |
| GPT-4o             | ??%      | $0.0??     | ??s         |
| Claude Haiku 4.5   | ??%      | $0.0??     | ??s         |
| Llama 3.3 (local)  | ??%      | $0.000     | ??s         |
```

**Criterio de done:** JSON de resultados por modelo + tabla markdown generada.

### Sesión 6.2 — README + Visuales

**Objetivo:** El README es la landing page. En 30 segundos alguien decide si le interesa.

**Estructura del README:**
1. **Hero:** 1 línea + tabla multi-LLM + badge accuracy
2. **GIF animado:** terminal con agente resolviendo pregunta en tiempo real
3. **Quick Start:** clone → docker compose up → preguntar (5 min)
4. **Architecture diagram:** Mermaid o SVG (no ASCII art)
5. **Benchmark evolution chart:** curva 60% → 93% como imagen
6. **"Why not LangChain?":** 1 párrafo que muestra pensamiento propio
7. **LATAM section:** diseñado para Argentina/LATAM, no un wrapper genérico
8. **What's next:** tease Módulo 2 sin overcommit

**Visuales a producir:**
- [ ] GIF: `asciinema` o screen recording del agente en terminal
- [ ] Chart: curva de accuracy por experimento (matplotlib → PNG)
- [ ] Diagram: arquitectura en Mermaid (renderizado en README)
- [ ] Table: comparativa multi-LLM (datos de sesión 6.1)

### Sesión 6.3 — Blog Post

**Objetivo:** El README muestra resultados. El blog muestra EL PROCESO. Esto es lo que abre puertas.

**Título:** "Building a FHIR Agent from 60% to 93% — Lessons from benchmark-driven AI development"

**Estructura:**
1. El problema: consultar datos de salud en LATAM es difícil
2. Por qué un agent y no RAG o fine-tuning
3. La curva: cada fix con antes/después
   - Pagination: +22pp
   - Code interpreter: +8pp
   - Query planner: +9pp
   - Terminology (ATC): +3pp
4. Lo que los LLMs no saben: terminología médica, FHIR syntax, códigos reales
5. Multi-LLM results: la tabla
6. Cost optimization: de $0.09 a $0.06/query
7. Lo que viene: visión sin overcommit

**Publicar en:** dev.to (audiencia técnica) + LinkedIn (decisores salud) + HN (viralidad potencial)

### Sesión 6.4 — Video Demo + Distribución

**Objetivo:** Publicar y medir tracción real.

**Video (3-5 min):**
1. `docker compose up` → datos cargados
2. Pregunta simple → respuesta correcta
3. Pregunta compleja (multi-hop) → agente razonando paso a paso
4. Trace en Langfuse → observabilidad completa
5. Tabla de benchmark → credibilidad

**Distribución:**
- [ ] GitHub release (tag v1.0.0)
- [ ] dev.to blog post
- [ ] LinkedIn post (personal + artículo)
- [ ] Reddit: r/healthIT, r/FHIR, r/MachineLearning, r/LanguageTechnology
- [ ] FHIR Chat (Zulip)
- [ ] HN: Show HN
- [ ] Twitter/X

## Posicionamiento (cómo se lee el proyecto)

El proyecto tiene que funcionar para 4 audiencias simultáneamente:

| Audiencia | Lo que ven | Lo que concluyen |
|-----------|-----------|------------------|
| **Hiring managers / AI teams** | Benchmark rigor, multi-LLM, ADRs, 94% coverage | "Este tipo sabe construir AI systems en serio" |
| **Health tech people** | FHIR R4, SNOMED CT AR, openRSD, locale packs | "Entiende el dominio, no es un tourist" |
| **Desarrolladores (HN/Reddit)** | Architecture, no-LangChain, demo funcional | "Buen proyecto, lo voy a probar" |
| **Potenciales clientes/partners** | Resultados + visión módulos 2-5 | "Si necesito algo de salud + AI, hablo con este" |

**Frase clave para el README:**
> "SaludAI is a benchmarked FHIR agent for Latin America. Module 1 is open source. If your health organization needs AI that understands clinical data, let's talk."

## Presupuesto

| Item | Costo |
|------|-------|
| Multi-LLM benchmark (GPT-4o + Haiku) | ~$3-5 |
| Blog hosting | $0 (dev.to) |
| Video | $0 (screen recording) |
| **Total** | **~$5** |

## Timeline estimado

4 sesiones de trabajo. Si es una sesión por día, listo en 1 semana.
