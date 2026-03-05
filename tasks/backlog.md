# SaludAI — Backlog

> Ideas y features que NO son parte del sprint actual.
> Si Claude o el desarrollador quieren agregar algo que no está en el ROADMAP, va acá.
> Revisar al planificar cada nuevo sprint.

---

## Deuda técnica / pendientes menores

- [x] ~~Crear ADR-002: No LangChain — custom agent loop~~ (completado sesión 3.4a)
- [x] ~~Crear ADR-004: Langfuse para observabilidad~~ (completado sesión 3.4a)
- [x] ~~Crear ADR-005: FHIR R4 only~~ (completado sesión 3.4a)
- [x] ~~Definir licencia del repo de datos sintéticos~~ → Apache 2.0 (sesión 4.6)
- [x] ~~Limpiar `saludai_core/data/`~~ — eliminado, `locales/ar/` es la unica fuente (sesión 4.6)
- [x] ~~Locale pack discovery via `importlib.metadata.entry_points(group="saludai.locales")`~~ (completado sesion 4.7)

## Query Builder — fuera de scope (posible Sprint 3+)

- [ ] Registro completo de search params válidos por resource type (validación estricta)
- [x] ~~Parámetro `_has` (reverse chaining)~~ (completado sesion 4.8)
- [ ] Composite parameters (e.g. `component-code-value-quantity`)
- [x] ~~`FHIRClient.execute(query)`~~ — convenience method implementado (sesión 4.6)

## FHIR Awareness Level 2 — Ejecucion → **planificado: sesión 4.9**

> ADR-008. Level 1 (awareness/metadata) implementado en sesion 3.6.
> Level 2 agrega ejecucion real: validacion, operaciones, parsing de extensions.

- [ ] Validar responses del agente contra profiles locales (StructureDefinition)
- [ ] Tool `$validate` que invoca la operacion del servidor FHIR
- [ ] Query builder aware de custom SearchParameters del locale pack
- [ ] Parsing inteligente de extensions en resultados FHIR (extraer y mostrar)
- [ ] Auto-sugerir search params del locale pack en el prompt del agente
- [ ] Tests e2e con servidor FHIR real que tenga profiles argentinos cargados

## REST API — extras (implementado base en 4.3)

> Base implementada: `POST /query` + `GET /health` + OpenAPI docs.
> Extras opcionales para el futuro:

- [ ] Exponer los 4 tools como endpoints individuales (`/resolve`, `/search`, `/resource`)
- [ ] WebSocket streaming para respuestas incrementales
- [ ] Rate limiting y API keys

## Ideas para sprints futuros

- [ ] FHIR Subscriptions support (real-time notifications)
- [ ] GraphQL interface (además de REST y MCP)
- [ ] Prompt versioning con A/B testing automatizado
- [ ] Web UI para explorar traces de Langfuse con contexto clínico
- [ ] Plugin system para agregar nuevos terminologies sin tocar core
- [ ] Benchmark propio con Q&A pairs argentinos (extensión de FHIR-AgentBench)
- [ ] Integration tests con servidor FHIR real del MSAL (requiere credenciales)
- [ ] Multi-language support (portugués para Brasil) — ahora posible con locale packs
- [ ] Rate limiting inteligente basado en costo de tokens

## Ideas para otros módulos (NO tocar en Etapa 1)

- [ ] M2: OCR pipeline para informes de laboratorio escaneados
- [ ] M3: Dashboard de vigilancia epidemiológica (TypeScript/React)
- [ ] M3: Integración con SNVS
- [ ] M4: Base de datos de interacciones medicamentosas
- [ ] M5: Modelo predictivo de demanda con Prophet
