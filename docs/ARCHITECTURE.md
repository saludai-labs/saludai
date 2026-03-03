# SaludAI — Arquitectura Técnica

> Documento vivo. Se actualiza con cada decisión arquitectónica relevante.
> Decisiones individuales se registran en `docs/decisions/` como ADRs.

---

## 1. Visión Arquitectónica

SaludAI es una plataforma modular donde cada módulo es un paquete independiente que comparte infraestructura base. El diseño prioriza:

1. **Auditabilidad** — Cada decisión del agente es trazable (Langfuse). En salud, esto no es negociable.
2. **Precisión sobre velocidad** — Preferimos un agente que tarda 10s y responde bien, a uno que tarda 2s y alucina códigos LOINC.
3. **Modularidad** — Cada paquete se puede usar independientemente. `saludai-core` sin el agente, el agente sin el MCP server.
4. **Extensibilidad** — Nuevos módulos (M2-M5) se construyen sobre los anteriores sin reescrituras.

---

## 2. Evaluación de Stack Tecnológico

### 2.1 Lenguaje primario: Python — con escapatorias estratégicas

**Decisión:** Python es el lenguaje principal. Componentes específicos de alto rendimiento pueden implementarse en Rust o TypeScript cuando haya justificación concreta.

**Por qué Python:**

| Factor | Evaluación |
|--------|-----------|
| Ecosistema FHIR | `fhir.resources`, `fhirclient`, HAPI test utils — todo Python-first |
| Ecosistema LLM/AI | Anthropic SDK, OpenAI SDK, Langfuse, MCP SDK — Python tiene soporte de primer nivel |
| Velocidad de desarrollo | Para un proyecto con 1 desarrollador, la velocidad de iteración es crítica |
| Comunidad de salud digital | La comunidad de health informatics es mayoritariamente Python + R |
| UV + Ruff | Herramientas modernas que resuelven los problemas históricos de Python (packaging, linting) |

**Dónde NO usar Python (escapatorias planificadas):**

| Componente | Lenguaje alternativo | Cuándo | Justificación |
|-----------|---------------------|--------|---------------|
| Terminology server de alta performance | **Rust** (o usar Snowstorm en Java) | Etapa 2+ si el resolver local es bottleneck | Fuzzy matching + trie traversal sobre millones de conceptos SNOMED es CPU-bound |
| CLI distribuible sin runtime | **Rust** (vía PyO3) o **Go** | Etapa 4+ si se quiere single-binary | Python requiere runtime instalado; Rust/Go compilan a binarios estáticos |
| Frontend / dashboard | **TypeScript** (React/Next.js) | Etapa 3 (Surveillance dashboard) | El dashboard de vigilancia epidemiológica necesita UI rica |
| MCP server (alternativa) | **TypeScript** | Solo si la comunidad MCP migra mayoritariamente a TS | Hoy el MCP SDK de Python es de primer nivel; mantener ojo en la evolución |
| Procesamiento masivo de documentos | **Rust** vía `pyo3` | Etapa 2 si OCR + NER es bottleneck | PDF parsing + NER sobre miles de documentos es memory/CPU intensive |

**Regla pragmática:** No introducir un segundo lenguaje hasta que haya un benchmark que demuestre que Python es el bottleneck para ese componente específico. "Podría ser más rápido en Rust" no es justificación suficiente — "Python tarda 45s por documento y necesitamos < 5s" sí lo es.

### 2.2 Lenguajes evaluados y descartados (para el core)

| Lenguaje | Fortalezas para este proyecto | Descartado porque |
|----------|------------------------------|-------------------|
| **Kotlin/Scala (JVM)** | HAPI FHIR es Java nativo; el desarrollador tiene 12+ años de JVM | Ecosistema LLM/AI es Python-first; duplica esfuerzo de integración; MCP SDK no tiene soporte JVM oficial |
| **Go** | Compilación rápida, binarios estáticos, buen networking | Ecosistema FHIR y LLM pobre; verbose para data transformation; no hay equivalente a fhir.resources |
| **Rust** | Performance, memory safety, WASM | Curva de aprendizaje alto para prototipado rápido; ecosistema FHIR inexistente; reservado para componentes puntuales |
| **TypeScript** | MCP SDK nativo, frontend unificado | Para backend FHIR + AI, las librerías son menos maduras que Python; se usará para frontend cuando llegue el momento |

### 2.3 Stack definitivo (Etapa 1)

```yaml
Lenguaje:       Python 3.12+
Package mgr:    UV (workspaces para monorepo)
Linting:        Ruff (format + lint + isort)
Type checking:  mypy (strict mode) — gradual adoption
Testing:        Pytest + pytest-asyncio + pytest-cov
HTTP:           httpx (async-first, reemplaza requests)
FHIR:           fhir.resources (modelos Pydantic) + httpx (client)
LLM:            Anthropic SDK + OpenAI SDK + Ollama (vía OpenAI-compatible API)
MCP:            mcp (Python SDK oficial de Anthropic)
API:            FastAPI + Pydantic v2
Tracing:        Langfuse Python SDK
Logging:        structlog (structured, JSON-friendly)
Config:         pydantic-settings (env vars + .env)
DB (Langfuse):  PostgreSQL 16 (solo para Langfuse, no para la app)
FHIR Server:    HAPI FHIR R4 (Docker)
Datos:          Synthea (customizado Argentina)
CI:             GitHub Actions
Container:      Docker + Docker Compose
```

---

## 3. Arquitectura de Componentes

### 3.1 Diagrama de alto nivel

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERFACES                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  MCP Server   │  │  REST API    │  │  CLI / Notebook  │  │
│  │  (saludai-mcp)│  │  (saludai-   │  │  (demos/eval)    │  │
│  │               │  │   api)       │  │                  │  │
│  └──────┬────────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └──────────────────┼───────────────────┘             │
│                            ▼                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           OBSERVABILITY LAYER (Langfuse)              │   │
│  │  Every LLM call, tool use, and agent step is traced   │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        AGENT LOOP (saludai-agent)                     │   │
│  │                                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ PLAN     │→ │ EXECUTE  │→ │ EVALUATE │→ loop/stop│   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  │  max_iterations: 5                                    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        TOOLKIT (tools available to the agent)         │   │
│  │                                                       │   │
│  │  • FHIR Query Builder    • Terminology Resolver       │   │
│  │  • Reference Navigator   • Code Interpreter           │   │
│  │  • AR Profile Validator                               │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        CORE LAYER (saludai-core)                      │   │
│  │                                                       │   │
│  │  • FHIRClient (httpx, async, multi-server)            │   │
│  │  • TerminologyService (SNOMED CT AR, CIE-10, LOINC)  │   │
│  │  • LLMClient (abstract → Anthropic/OpenAI/Ollama)    │   │
│  │  • Types (Pydantic models for all shared data)        │   │
│  │  • Config (pydantic-settings, env-based)              │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        INFRASTRUCTURE                                 │   │
│  │  HAPI FHIR R4  │  Langfuse  │  PostgreSQL  │ Synthea │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Paquetes y responsabilidades

#### `saludai-core` — La base que todo reutiliza

```
Responsabilidades:
  - FHIRClient: conexión a servidores FHIR (async httpx)
    - Multi-server support (HAPI, openRSD, cualquier R4)
    - Auth: OAuth2 / SMART on FHIR / API key / none
    - Retry con exponential backoff
    - Connection pooling
    - Response caching (configurable TTL)
  
  - TerminologyService: resolución de códigos
    - SNOMED CT (edición argentina)
    - CIE-10 (adaptación argentina)
    - LOINC
    - Fuzzy matching (para lenguaje natural → código)
    - Caching de resoluciones
  
  - LLMClient: abstracción de proveedor
    - Interface: generate(prompt, tools?, temperature?) → response
    - Implementations: AnthropicClient, OpenAIClient, OllamaClient
    - Auto-tracing via Langfuse decorator
    - Streaming support
  
  - Types: modelos Pydantic compartidos
    - FHIRQueryParams, TerminologyResult, AgentTrace, etc.
    - Validación estricta en boundaries
  
  - Config: pydantic-settings
    - Carga desde .env / env vars / defaults
    - Typed, validado, documentado
  
  - Exceptions: jerarquía custom
    - SaludAIError → FHIRError, TerminologyError, LLMError, AgentError

No depende de: ningún otro paquete de SaludAI
Dependido por: todos los demás paquetes
```

#### `saludai-agent` — El cerebro

```
Responsabilidades:
  - AgentLoop: orquestación del ciclo plan→execute→evaluate
    - Single-turn (Sprint 2) → Multi-turn con self-correction (Sprint 3)
    - Max iterations configurable (default: 5)
    - Exit conditions: answer found, max iterations, error
    - Full Langfuse trace por ejecución
  
  - Tools (disponibles para el agente):
    - fhir_query: construye y ejecuta queries FHIR
    - terminology_lookup: resuelve texto → códigos
    - reference_navigator: sigue refs entre recursos (Sprint 3)
    - code_interpreter: ejecuta Python sandboxed (Sprint 3)
    - ar_profile_validator: valida contra perfiles openRSD (Sprint 3)
  
  - Prompts: templates de system/user prompts
    - Versionados (para A/B testing en benchmarks)
    - En español e inglés

Depende de: saludai-core
```

#### `saludai-mcp` — Interfaz para Claude Desktop y agentes

```
Responsabilidades:
  - MCP Server con tools:
    - fhir_query: consulta en lenguaje natural
    - patient_summary: resumen clínico de un paciente
    - terminology_lookup: buscar códigos desde texto
    - population_stats: estadísticas poblacionales
    - data_quality_check: verificar calidad de datos
  
  - Formato MCP estándar (compatible con Claude Desktop)
  - Instalable como: `saludai serve` o `uvx saludai-mcp`

Depende de: saludai-core, saludai-agent
```

#### `saludai-api` — REST API para integración

```
Responsabilidades:
  - FastAPI application
  - Mismos endpoints que el MCP server, pero REST
  - OpenAPI docs auto-generadas (/docs)
  - Health check, readiness, liveness endpoints
  - Rate limiting básico
  - CORS configurado para futuros frontends

Depende de: saludai-core, saludai-agent
```

---

## 4. Patrones Clave

### 4.1 Agent Loop (el patrón central)

```python
# Pseudocódigo del self-reasoning loop
async def run(query: str, max_iterations: int = 5) -> AgentResult:
    context = AgentContext(query=query)
    
    for i in range(max_iterations):
        # 1. PLAN: el LLM decide qué hacer
        plan = await llm.plan(context)
        trace.log_step("plan", plan)
        
        # 2. EXECUTE: ejecutar las herramientas elegidas
        for tool_call in plan.tool_calls:
            result = await execute_tool(tool_call)
            context.add_result(result)
            trace.log_step("execute", tool_call, result)
        
        # 3. EVALUATE: ¿tenemos lo que necesitamos?
        evaluation = await llm.evaluate(context)
        trace.log_step("evaluate", evaluation)
        
        if evaluation.has_answer:
            return AgentResult(
                answer=evaluation.answer,
                confidence=evaluation.confidence,
                sources=context.sources,
                trace_id=trace.id
            )
    
    return AgentResult(answer="No pude encontrar una respuesta completa.", ...)
```

### 4.2 LLM Client abstraction

```python
# Interface que todos los providers implementan
class LLMClient(Protocol):
    async def generate(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse: ...

# Implementaciones: AnthropicClient, OpenAIClient, OllamaClient
# Selección via config: SALUDAI_LLM_PROVIDER=anthropic|openai|ollama
```

### 4.3 Terminology resolution con fallback

```
1. Exact match en cache local → hit? return
2. Exact match en ValueSet conocido (SNOMED AR, CIE-10 AR) → hit? return
3. Fuzzy match (Levenshtein + token overlap) → score > threshold? return
4. LLM-assisted resolution → "¿Qué código SNOMED CT corresponde a X?" → validate
5. Si nada funciona → return with low confidence + flag para human review
```

### 4.4 Configuration

```python
# Toda la config es via environment variables, tipada con Pydantic
class SaludAIConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALUDAI_")
    
    # FHIR
    fhir_server_url: str = "http://localhost:8080/fhir"
    fhir_auth_type: Literal["none", "bearer", "oauth2"] = "none"
    
    # LLM
    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    llm_model: str = "claude-sonnet-4-5-20250929"
    llm_temperature: float = 0.0
    
    # Ollama (desarrollo local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    
    # Langfuse
    langfuse_enabled: bool = True
    langfuse_host: str = "http://localhost:3000"
    
    # Agent
    agent_max_iterations: int = 5
    agent_timeout_seconds: int = 60
```

---

## 5. Decisiones de Infraestructura

### 5.1 Docker Compose (desarrollo)

```yaml
services:
  hapi-fhir:     # FHIR R4 server con datos sintéticos argentinos
  langfuse:      # Observability dashboard
  langfuse-db:   # PostgreSQL para Langfuse
  # Future (Etapa 2+):
  # snowstorm:   # SNOMED CT terminology server
  # saludai-api: # FastAPI containerized
```

### 5.2 CI/CD (GitHub Actions)

```
on push:
  - ruff check + format
  - mypy (gradual, primero solo saludai-core)
  - pytest (all packages)
  - coverage report
  
on PR to main:
  - todo lo anterior +
  - benchmark eval (FHIR-AgentBench)
  - benchmark score comparison vs main
```

### 5.3 Datos sintéticos (Synthea Argentina)

Synthea genera pacientes FHIR R4 realistas. Lo customizamos para Argentina:
- Nombres y apellidos argentinos (fuente: padrón electoral público)
- DNI en formato argentino
- Provincias y ciudades como Location/Organization
- Patologías prevalentes: Chagas, dengue, tuberculosis, desnutrición infantil
- Códigos CIE-10 y SNOMED CT edición argentina

Esto vive en un repo separado (`saludai-data-ar`) porque es valioso por sí solo para la comunidad.

---

## 6. Seguridad y Compliance

- **No se almacenan datos de pacientes reales** en el repo ni en el agente.
- Datos sintéticos solamente para desarrollo y demos.
- Pilotos con datos reales se hacen en infraestructura del cliente, nunca en la nuestra.
- Secrets via env vars, nunca en código. `.env.example` con dummies.
- FHIR server auth es configurable (none para dev, OAuth2/SMART para producción).
- Langfuse traces pueden contener datos sensibles → self-hosted recommended para producción.

---

## 7. Extensibilidad para Etapas Posteriores

### Qué hereda cada módulo futuro

| Componente (Etapa 1) | M2: DocIntel | M3: Surveillance | M4: CDS | M5: PopHealth |
|----------------------|:---:|:---:|:---:|:---:|
| FHIRClient | ✓ | ✓ | ✓ | ✓ |
| TerminologyService | ✓ | ✓ | ✓ | ✓ |
| LLMClient | ✓ | ✓ | ✓ | ✓ |
| AgentLoop | — | ✓ | ✓ | ✓ |
| Langfuse tracing | ✓ | ✓ | ✓ | ✓ |
| Docker infra | ✓ | ✓ | ✓ | ✓ |
| CI pipeline | ✓ | ✓ | ✓ | ✓ |
| Config system | ✓ | ✓ | ✓ | ✓ |

### Cómo se agregan módulos nuevos

```
packages/
  saludai-core/          # Ya existe (Etapa 1)
  saludai-agent/         # Ya existe (Etapa 1)
  saludai-mcp/           # Ya existe (Etapa 1)
  saludai-api/           # Ya existe (Etapa 1)
  saludai-docintell/     # NUEVO (Etapa 2) — hereda core + agent
  saludai-surveillance/  # NUEVO (Etapa 3) — hereda core + agent, en repo privado
```

Los módulos premium (M3-M5) viven en el repo privado `saludai-private` pero importan los paquetes públicos como dependencias normales vía PyPI.

---

## Registro de Cambios Arquitectónicos

| Fecha | ADR | Decisión |
|-------|-----|----------|
| 2026-03 | 001 | Monorepo con UV workspaces |
| 2026-03 | 002 | No LangChain — agent loop custom |
| 2026-03 | 003 | Python-first con polyglot estratégico |
| 2026-03 | 004 | Langfuse para observability |
| 2026-03 | 005 | FHIR R4 only |

Ver `docs/decisions/` para el detalle de cada ADR.
