# ADR-004: Langfuse for Observability

**Status:** Accepted

## Context

The FHIR Smart Agent needs full observability: traces of every LLM call, tool execution, latencies, tokens consumed, and results. This is critical for:

1. **Debugging:** understanding why the agent made an incorrect decision
2. **Benchmarking:** comparing prompt/tool changes with traceable metrics
3. **Clinical auditing:** in production, every medical query must be traceable
4. **Cost optimization:** monitoring token consumption per query

We need an LLM observability platform that supports hierarchical tracing (trace → generation → tool call).

## Decision

Use **Langfuse** as the observability platform for all LLM interactions in the agent.

Integration is through a custom `Tracer` protocol (not Langfuse's SDK decorator), keeping the code decoupled from the observability provider.

> **Note:** The decision to use Langfuse Cloud vs self-hosted is documented separately in ADR-006.

## Consequences

### Positive
- **Open source:** Langfuse is open source (MIT), aligned with the project's values
- **Hierarchical tracing:** supports trace → span → generation with arbitrary metadata
- **Full dashboard:** visualization of latencies, costs, scores, metadata filters
- **Integrated evaluations:** native support for scores/evaluations (useful for benchmarking)
- **Multi-provider:** works with Anthropic, OpenAI, Ollama — not tied to an LLM vendor
- **Generous free tier:** 50k observations/month on cloud, no limits on self-hosted
- **Python SDK:** official `langfuse` SDK with good async support

### Negative
- **External dependency:** one more library in the stack (though optional via `NoOpTracer`)
- **Send latency:** ~100ms extra per trace on cloud (mitigated by async batching)
- **Learning curve:** the tracing model (traces, spans, generations) has its complexity

### Risks
- If Langfuse changes its pricing model or stops being maintained, we'd need to migrate
- Mitigation: our `Tracer` protocol allows implementing an adapter to any other backend (Phoenix, LangSmith, custom) without changing agent code

## Alternatives Considered

### Option A: LangSmith
- Pros: native LangChain integration, mature dashboard
- Cons: proprietary (not open source), aggressive pricing, lock-in with LangChain ecosystem; we don't use LangChain (ADR-002)

### Option B: Arize Phoenix
- Pros: open source, good evaluation support
- Cons: more oriented toward generic ML ops than LLM tracing, smaller ecosystem, more complex setup

### Option C: Custom logging (structlog + files)
- Pros: no external dependencies, full control
- Cons: no dashboard, no integrated evaluations, requires building all visualization and analysis infrastructure

### Option D: OpenTelemetry + Grafana
- Pros: open standard, mature infrastructure
- Cons: no LLM-native abstractions (generations, tokens, prompts), significant integration effort for our use case

## References

- `packages/saludai-agent/src/saludai_agent/tracing.py` — Tracer protocol + LangfuseTracer + NoOpTracer
- `docs/decisions/006-langfuse-cloud.md` — Cloud vs self-hosted decision
- [Langfuse docs](https://langfuse.com/docs)
- [Langfuse GitHub](https://github.com/langfuse/langfuse)
