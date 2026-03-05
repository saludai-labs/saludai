# SaludAI — Roadmap de Desarrollo

> Etapa 1: Módulo 1 — FHIR Smart Agent
> Timeline: 4 sprints × 1 semana = 4 semanas
> Licencia: Apache 2.0 (100% open source)

---

## Visión General de Etapas

| Etapa | Módulo | Semanas | Licencia | Estado |
|-------|--------|---------|----------|--------|
| **1** | **FHIR Smart Agent** | **1-4** | **🟢 Open Source** | **← ESTAMOS AQUÍ** |
| 2 | Document Intelligence | 5-10 | 🟡 Open-Core | Planificación |
| 3 | Surveillance AI | 11-20 | 🔴 Propietario | Conceptual |
| 4 | Clinical Decision Support | 21-32 | 🔴 Propietario | Conceptual |
| 5 | Population Health | 33-44 | 🔴 Propietario | Conceptual |

Cada módulo hereda infraestructura de los anteriores. Las decisiones de la Etapa 1 son las más importantes porque son el cimiento.

---

## Objetivo Final Demostrable (Etapa 1)

Al cerrar el Sprint 4, este flujo debe funcionar sin fricción:

```
1. git clone https://github.com/saludai-labs/saludai.git
2. cd saludai && docker compose up -d     # HAPI FHIR + Langfuse + datos AR
3. Conectar MCP server en Claude Desktop
4. Preguntar: "¿Cuántos pacientes con hipertensión hay en Buenos Aires mayores de 50?"
5. Ver respuesta correcta + trace completo en Langfuse
6. README muestra benchmark score con badge
```

**Tiempo total de la demo: 5 minutos.**

---

## Sprint 1: Fundación (Semana 1)

**Meta:** Cualquiera clona, levanta, y ve datos FHIR argentinos en 5 minutos.

### Sesiones

| # | Tarea | Output verificable |
|---|-------|--------------------|
| 1.1 | ✅ Crear GitHub Org `saludai-labs`, repos, monorepo UV | `uv sync` funciona, repos creados |
| 1.2 | ✅ CLAUDE.md + GitHub Actions CI + pre-commit hooks | CI verde en push, Ruff + Pytest en pipeline |
| 1.3 | ✅ Docker Compose: HAPI FHIR R4 + Synthea Argentina | `docker compose up` → FHIR server con datos AR |
| 1.4 | ✅ `saludai-core`: FHIR client (connect, search, read) | Tests pasan contra HAPI FHIR local |
| 1.5 | ✅ README, LICENSE (Apache 2.0), CONTRIBUTING.md | Repo público presentable |

### Definición de Done
- [x] `docker compose up` levanta HAPI FHIR con 50+ pacientes argentinos
- [x] `curl http://localhost:8080/fhir/Patient` retorna pacientes con nombres argentinos
- [x] `uv run pytest packages/saludai-core/` — todos los tests verdes (18 tests)
- [x] CI en GitHub Actions: lint + test en cada push
- [x] README con visión, quick start, y badge de CI

---

## Sprint 2: El Cerebro del Agente (Semana 2)

**Meta:** El agente responde consultas básicas en lenguaje natural con tracing visible.

### Sesiones

| # | Tarea | Output verificable |
|---|-------|--------------------|
| 2.1 | ✅ Terminology Resolver (SNOMED CT AR, CIE-10, LOINC) | "diabetes tipo 2" → SNOMED 44054006 con tests |
| 2.2 | ✅ FHIR Query Builder (search params, _include, chained) | Params estructurados → URL FHIR válida |
| 2.3 | ✅ Agent Loop v1: single-turn (plan → execute → evaluate) | Prompt → query → respuesta narrativa funcional |
| 2.4 | ✅ Langfuse integration (Tracer protocol + instrumentation) | Traces visibles en Langfuse Cloud |
| 2.5 | ✅ FHIR-AgentBench: framework + 25 preguntas + baseline 88% | Score baseline documentado en README |
| 2.6 | ✅ Benchmark Honesto: seed enriquecido (536 entries), 50 preguntas, judge híbrido | Baseline honesto: **60% accuracy** (30/50) |

### Definición de Done
- [x] Consulta: "Pacientes con diabetes tipo 2 mayores de 60" → respuesta correcta
- [x] Langfuse Cloud mostrando traces con cada paso
- [x] Benchmark baseline score documentado: **60% accuracy** (30/50) — baseline honesto
- [x] Todos los tests verdes (344 tests), ruff limpio
- [x] `docs/experiments/EXPERIMENTS.md` con resultados y análisis

---

## Sprint 3: Multi-turn y Precisión (Semana 3)

**Meta:** El agente itera, se autocorrige, navega referencias, y sube 15-20 puntos de benchmark.

### Sesiones

| # | Tarea | Output verificable |
|---|-------|--------------------|
| 3.1 ✅ | Pagination + `_summary=count` | Benchmark 60% → 82% |
| 3.2 ✅ | Reference Navigator + Fixes | Benchmark 82% → 86%, 0 errors |
| 3.3 ✅ | Code Interpreter tool (sandboxed Python execution) | Benchmark 86% → 94%, agente calcula/agrupa con código |
| 3.4 ✅ | Locale packs + deuda técnica (ADRs, coverage, extensibilidad) | `load_locale_pack("ar")`, ADR-007, 375 tests |
| 3.5 ✅ | Re-eval benchmark + judge fix + timeout bump | Benchmark 94% → 98%, judge regex fix, 0 false negatives |
| 3.6 ✅ | FHIR Awareness en locale packs (Level 1) | 6 tipos nuevos, AR pack con openRSD, prompt dinamico, ADR-008 |

### Definición de Done
- [ ] "Medicaciones activas de pacientes con insuficiencia cardíaca" → navega refs correctamente
- [ ] Self-correction visible en Langfuse (agente replanifica tras resultado parcial)
- [x] Benchmark: +38 puntos sobre Sprint 2 baseline (60% → 98%)
- [x] Coverage ≥ 70% (84.57% — sesión 3.4a)

---

## Sprint 4: Producto y Lanzamiento (Semana 4)

**Meta:** MCP Server funcional, pip install operativo, blog publicado, demo grabada.

### Sesiones

| # | Tarea | Output verificable |
|---|-------|--------------------|
| 4.1 ✅ | MCP Server: FastMCP + 4 tools + CLI entry point + 17 tests | `uv run saludai-mcp` funcional |
| 4.2 ✅ | REST API `/query` + CLI `saludai query` | Agent loop accesible via HTTP y terminal |
| 4.3 ✅ | PyPI packaging + Docker image | Meta-paquete, Dockerfile, CI publish workflow |
| 4.4 ✅ | 3 Jupyter notebooks + README final con badges | Notebooks ejecutables con output |
| 4.5 | Blog post + video demo 5 min + publicar en comunidades | Blog en dev.to, video en YouTube |
| 4.6 ✅ | Quick wins: limpiar data/, licencia datos, `execute(query)` | CSVs redundantes eliminados, licencia definida, convenience method con tests |
| 4.7 ✅ | Locale pack discovery via `entry_points` | Paquetes externos pueden registrar locale packs sin tocar core |
| 4.8 ✅ | Parámetro `_has` (reverse chaining) en Query Builder | `_has` funcional con tests, queries complejas habilitadas |
| 4.9 ✅ | FHIR Awareness Level 2 — extension parsing + custom search params | Extension-aware summarizer, AR custom search params, prompt con datos reales |

### Definición de Done
- [ ] `pip install saludai && saludai serve` → MCP server corriendo
- [ ] Video de 5 min: clone → demo en Claude Desktop
- [ ] Blog publicado: "Por qué los FHIR agents genéricos fallan en el 50%"
- [ ] README con métricas, badges, screenshots
- [ ] Coverage ≥ 70%, benchmark score publicado
- [ ] `saludai_core/data/` eliminado, sin imports rotos
- [ ] `FHIRClient.execute(query)` funcional con tests
- [ ] Locale packs descubribles via `entry_points`
- [ ] `_has` en Query Builder con tests
- [x] Extension-aware resource summarizer (parsing + display en tools)
- [x] AR custom search params en locale pack + prompt

---

## Métricas de Éxito (Etapa 1 completa)

| Métrica | Target mínimo | Target óptimo |
|---------|---------------|---------------|
| FHIR-AgentBench accuracy | 55% | 70%+ |
| Setup time (clone → running) | < 10 min | < 5 min |
| GitHub stars (primer mes) | 20 | 50+ |
| Test coverage | 70% | 85%+ |
| Latencia promedio por query | < 15s | < 8s |

---

## Conexión con Etapas Posteriores

Cada etapa hereda y extiende lo anterior:

| Etapa | Hereda de Etapa 1 | Agrega |
|-------|-------------------|--------|
| 2 - Document Intelligence | FHIR client, terminology, Langfuse, Docker | OCR, NER clínico, PDF→FHIR |
| 3 - Surveillance AI | Todo anterior + agent loop + data pipeline | Anomalía detection, alertas, reportes SNVS |
| 4 - Clinical Decision Support | Todo anterior + drug/guideline DBs | Interacciones, adherencia a guías |
| 5 - Population Health | Todo anterior + analytics engine | Dashboards, predicción, eval programas |

**Regla:** Las decisiones de Etapa 1 deben ser lo suficientemente genéricas para que las etapas posteriores no necesiten reescrituras. Por eso el FHIR client, el terminology resolver, y el agent loop son paquetes separados.
