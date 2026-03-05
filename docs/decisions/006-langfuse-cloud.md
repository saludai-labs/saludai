# ADR-006: Langfuse Cloud (free tier) para desarrollo

**Estado:** Aceptada
**Autor:** SaludAI

## Contexto

Langfuse es nuestra herramienta de observability para tracear llamadas LLM, ejecuciones del agente, y uso de tools. Existen dos opciones de deployment:

1. **Self-hosted:** Langfuse + PostgreSQL en Docker Compose local
2. **Cloud:** Langfuse Cloud (cloud.langfuse.com) con free tier

Para desarrollo en Etapa 1, necesitamos decidir cuál usar. La prioridad es simplicidad de setup y velocidad de iteración.

## Decisión

Usar **Langfuse Cloud (free tier)** para desarrollo. No incluir containers de Langfuse en el docker-compose.yml local.

## Consecuencias

### Positivas
- Docker Compose más liviano (solo HAPI FHIR + seed sidecar)
- Menor uso de recursos locales (no PostgreSQL + Langfuse containers)
- Setup más rápido para nuevos contribuidores
- Dashboard accesible desde cualquier lugar (no solo localhost)
- Sin mantenimiento de infraestructura Langfuse

### Negativas
- Dependencia de servicio externo para traces
- Latencia de envío de traces (~100ms vs ~1ms local)
- Free tier tiene límite de 50k observaciones/mes
- Datos de traces viajan a servidores de Langfuse (no un problema para datos sintéticos)

### Riesgos
- Si el free tier se queda corto, migrar a self-hosted requiere agregar containers
- Mitigación: la migración es solo cambiar env vars + agregar services al docker-compose

## Alternativas consideradas

### Opción A: Self-hosted desde el inicio
- Pros: Control total, sin límites, sin dependencias externas
- Contras: 2 containers extra (Langfuse + PostgreSQL), más recursos, más complejidad de setup

### Opción B: Sin Langfuse hasta Sprint 2
- Pros: Máxima simplicidad en Sprint 1
- Contras: Perdemos visibilidad desde el inicio; la integración tardía es más costosa

## Referencias

- `docs/knowledge/langfuse-setup.md` — investigación detallada
- [Langfuse Cloud free tier](https://langfuse.com/pricing)
- [Langfuse self-hosting docs](https://langfuse.com/docs/deployment/self-host)
