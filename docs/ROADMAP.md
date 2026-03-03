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
| 2.1 | Terminology Resolver (SNOMED CT AR, CIE-10, LOINC) | "diabetes tipo 2" → SNOMED 44054006 con tests |
| 2.2 | FHIR Query Builder (search params, _include, chained) | Params estructurados → URL FHIR válida |
| 2.3 | Agent Loop v1: single-turn (plan → execute → evaluate) | Prompt → query → respuesta narrativa funcional |
| 2.4 | Langfuse integration + Docker Compose actualizado | Traces visibles en dashboard local |
| 2.5 | FHIR-AgentBench: clonar, setup, primer eval baseline | Score baseline documentado en README |

### Definición de Done
- [ ] Consulta: "Pacientes con diabetes tipo 2 mayores de 60" → respuesta correcta
- [ ] Langfuse en `http://localhost:3000` mostrando traces con cada paso
- [ ] Benchmark baseline score documentado (aun si es ~40-50%)
- [ ] Todos los tests verdes, coverage ≥ 60%

---

## Sprint 3: Multi-turn y Precisión (Semana 3)

**Meta:** El agente itera, se autocorrige, navega referencias, y sube 15-20 puntos de benchmark.

### Sesiones

| # | Tarea | Output verificable |
|---|-------|--------------------|
| 3.1 | Multi-turn loop (max_iterations=5, exit conditions) | Agente replanifica si resultado incompleto |
| 3.2 | Reference Navigator (resolve refs, multi-hop) | MedicationRequest → Medication → detalles |
| 3.3 | Code Interpreter tool (sandboxed Python execution) | Agente calcula promedios, filtra, agrupa |
| 3.4 | AR Profile Validator + mejoras terminology | Validación contra perfiles openRSD |
| 3.5 | Re-eval benchmark + prompt optimization | Score mejorado, before/after en README |

### Definición de Done
- [ ] "Medicaciones activas de pacientes con insuficiencia cardíaca" → navega refs correctamente
- [ ] Self-correction visible en Langfuse (agente replanifica tras resultado parcial)
- [ ] Benchmark: +15-20 puntos sobre Sprint 2 baseline
- [ ] Coverage ≥ 70%

---

## Sprint 4: Producto y Lanzamiento (Semana 4)

**Meta:** MCP Server funcional, pip install operativo, blog publicado, demo grabada.

### Sesiones

| # | Tarea | Output verificable |
|---|-------|--------------------|
| 4.1 | MCP Server: todos los tools + tests e2e | MCP funcional con all tools |
| 4.2 | FastAPI REST API + OpenAPI docs | `/docs` documentada, misma funcionalidad que MCP |
| 4.3 | PyPI packaging + Docker image publicada | `pip install saludai` funcional |
| 4.4 | 3 Jupyter notebooks + README final con badges | Notebooks ejecutables con output |
| 4.5 | Blog post + video demo 5 min + publicar en comunidades | Blog en dev.to, video en YouTube |

### Definición de Done
- [ ] `pip install saludai && saludai serve` → MCP server corriendo
- [ ] Video de 5 min: clone → demo en Claude Desktop
- [ ] Blog publicado: "Por qué los FHIR agents genéricos fallan en el 50%"
- [ ] README con métricas, badges, screenshots
- [ ] Coverage ≥ 70%, benchmark score publicado

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
