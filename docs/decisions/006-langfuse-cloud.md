# ADR-006: Langfuse Cloud (Free Tier) for Development

**Status:** Accepted

## Context

Langfuse is our observability tool for tracing LLM calls, agent executions, and tool usage. Two deployment options exist:

1. **Self-hosted:** Langfuse + PostgreSQL in local Docker Compose
2. **Cloud:** Langfuse Cloud (cloud.langfuse.com) with free tier

For development, we need to decide which to use. The priority is setup simplicity and iteration speed.

## Decision

Use **Langfuse Cloud (free tier)** for development. Do not include Langfuse containers in the local docker-compose.yml.

## Consequences

### Positive
- Lighter Docker Compose (only HAPI FHIR + seed sidecar)
- Lower local resource usage (no PostgreSQL + Langfuse containers)
- Faster setup for new contributors
- Dashboard accessible from anywhere (not just localhost)
- No Langfuse infrastructure maintenance

### Negative
- Dependency on external service for traces
- Trace send latency (~100ms vs ~1ms local)
- Free tier has a 50k observations/month limit
- Trace data travels to Langfuse servers (not a concern for synthetic data)

### Risks
- If the free tier becomes insufficient, migrating to self-hosted requires adding containers
- Mitigation: migration is just changing env vars + adding services to docker-compose

## Alternatives Considered

### Option A: Self-hosted from the start
- Pros: full control, no limits, no external dependencies
- Cons: 2 extra containers (Langfuse + PostgreSQL), more resources, more setup complexity

### Option B: No Langfuse initially
- Pros: maximum simplicity at the start
- Cons: lose visibility from day one; late integration is more costly

## References

- [Langfuse Cloud free tier](https://langfuse.com/pricing)
- [Langfuse self-hosting docs](https://langfuse.com/docs/deployment/self-host)
