# SaludAI — Backlog

> Ideas y features que NO son parte del sprint actual.
> Si Claude o el desarrollador quieren agregar algo que no está en el ROADMAP, va acá.
> Revisar al planificar cada nuevo sprint.

---

## Deuda técnica / pendientes menores

- [ ] Crear ADR-002: No LangChain — custom agent loop (referenciado en CLAUDE.md)
- [ ] Crear ADR-004: Langfuse para observabilidad (referenciado en CLAUDE.md)
- [ ] Crear ADR-005: FHIR R4 only (referenciado en CLAUDE.md)
- [ ] Definir licencia del repo de datos sintéticos (¿Apache 2.0? ¿CC-BY-4.0?)

## Query Builder — fuera de scope (posible Sprint 3+)

- [ ] Registro completo de search params válidos por resource type (validación estricta)
- [ ] Parámetro `_has` (reverse chaining)
- [ ] Composite parameters (e.g. `component-code-value-quantity`)
- [ ] `FHIRClient.execute(query)` — convenience method que acepta `FHIRQuery` directamente (sesión 2.3)

## Ideas para sprints futuros

- [ ] FHIR Subscriptions support (real-time notifications)
- [ ] GraphQL interface (además de REST y MCP)
- [ ] Prompt versioning con A/B testing automatizado
- [ ] Web UI para explorar traces de Langfuse con contexto clínico
- [ ] Plugin system para agregar nuevos terminologies sin tocar core
- [ ] Benchmark propio con Q&A pairs argentinos (extensión de FHIR-AgentBench)
- [ ] Integration tests con servidor FHIR real del MSAL (requiere credenciales)
- [ ] Multi-language support (portugués para Brasil)
- [ ] Rate limiting inteligente basado en costo de tokens

## Ideas para otros módulos (NO tocar en Etapa 1)

- [ ] M2: OCR pipeline para informes de laboratorio escaneados
- [ ] M3: Dashboard de vigilancia epidemiológica (TypeScript/React)
- [ ] M3: Integración con SNVS
- [ ] M4: Base de datos de interacciones medicamentosas
- [ ] M5: Modelo predictivo de demanda con Prophet
