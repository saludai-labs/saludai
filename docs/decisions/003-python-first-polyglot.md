# ADR-003: Python-first with Strategic Polyglot

**Status:** Accepted

## Context

The AI/LLM ecosystem is predominantly Python-first. FHIR libraries, LLM SDKs (Anthropic, OpenAI), observability tools (Langfuse), and MCP all have Python as a first-class citizen. However, there are components where Python may not be the best fit (distributable CLIs, rich UIs, CPU-bound processing).

## Decision

Python 3.12+ is the primary language for the entire project. Specific components may use other languages when a concrete benchmark justifies it.

Approved alternatives:
- **Rust** (via PyO3): high-performance components (terminology trie, document processing)
- **TypeScript** (React/Next.js): dashboards and UIs
- **Go**: distributable CLIs as single binaries

Rule: don't introduce a second language until a benchmark proves Python is the bottleneck for that specific component.

## Consequences

### Positive
- Direct access to the full LLM/AI ecosystem (Anthropic SDK, Langfuse, MCP SDK)
- UV + Ruff solve Python's historical packaging and linting problems
- Health informatics community is Python/R
- Fast prototyping: crucial for benchmark-driven agent development

### Negative
- Python is slow for CPU-bound tasks (mitigable with Rust via PyO3 when needed)
- Type system less strict than statically-typed languages (mitigable with mypy strict + Pydantic)

### Risks
- If the terminology resolver needs to process millions of SNOMED concepts in < 1s, Python won't suffice. Trigger: benchmark > 5s for resolution → evaluate Rust binding.
- If the MCP community migrates to TypeScript-only, the server would need porting. Low probability given Anthropic maintains the Python SDK.

## Alternatives Considered

### JVM (Kotlin/Scala)
- Pros: HAPI FHIR is Java-native, strong type safety
- Cons: LLM/AI ecosystem is Python-first; Anthropic SDK, Langfuse, MCP SDK have no official JVM support

### TypeScript
- Pros: native MCP SDK, frontend/backend unification
- Cons: FHIR libraries less mature, no equivalent to fhir.resources (Pydantic models)

### Go
- Pros: fast compilation, static binaries, excellent for CLI tools
- Cons: non-existent FHIR ecosystem, verbose for data transformation, poor LLM ecosystem
