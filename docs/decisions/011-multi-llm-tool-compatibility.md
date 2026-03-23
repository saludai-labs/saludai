# ADR-011: Multi-LLM Tool Compatibility — Schema Flattening and Param Tolerance

**Status:** Accepted

## Context

When expanding the benchmark to non-Anthropic models (GPT-4o, Llama 3.3, Qwen 3.5), we discovered that **GPT-4o doesn't generate the `params` field in tool calls** for simple filtered queries.

### The concrete problem

Our FHIR tools (`count_fhir`, `search_fhir`) use a standard Anthropic pattern:

```json
{
  "properties": {
    "resource_type": {"type": "string"},
    "params": {
      "type": "object",
      "additionalProperties": {"type": "string"},
      "description": "FHIR search parameters..."
    }
  },
  "required": ["resource_type"]
}
```

- **Claude Sonnet:** generates `{"resource_type": "Patient", "params": {"gender": "male"}}` ✅
- **Llama 3.3 70B:** generates `{"resource_type": "Patient", "params": {"gender": "male"}}` ✅
- **Qwen 3.5 9B:** generates `{"resource_type": "Patient", "params": {"gender": "male"}}` ✅
- **GPT-4o:** generates `{"resource_type": "Patient"}` ❌ (omits `params` entirely)

### Root cause analysis

The behavior is consistent with a known OpenAI function calling limitation:

1. **`additionalProperties` in nested objects** is poorly supported by GPT-4o. The model doesn't "understand" it can put any key inside an open object.
2. **`strict: true`** from OpenAI (Structured Outputs) directly prohibits `additionalProperties: true`, confirming this isn't a well-supported pattern in their stack.
3. The `params` field is **optional** (`required` only includes `resource_type`), giving the model "permission" to omit it.
4. At top-level, with `additionalProperties` on the root schema, GPT-4o does generate additional keys consistently.

### Impact magnitude

Without fix, GPT-4o achieved **43.5% accuracy** on the first 23 questions. With fixes: **~96% on the same 23**.

## Decision

We implement a **two-layer multi-LLM compatibility pattern** that doesn't modify tool definitions or the Anthropic prompt:

### Layer 1: Schema Flattening for OpenAI (`_flatten_params_for_openai`)

In `llm.py`, `_tools_to_openai()` transforms the schema before sending to the OpenAI API:

```python
# Before (what Anthropic receives, unchanged):
{"properties": {"resource_type": ..., "params": {"additionalProperties": ...}}}

# After (what GPT-4o receives):
{"properties": {"resource_type": ...}, "additionalProperties": {"type": "string"}}
```

**IMPORTANT: flattening is conditional.** Only applied when `base_url is None` (native OpenAI). For Together AI and Ollama (`base_url` present), the schema is sent unchanged. Reason: Qwen 3.5 9B with flattened schema drops from 29% to 13% (empty responses in 82/86 cases — the model gets confused by `additionalProperties` at root level).

### Layer 2: Param Tolerance in the executor (`_merge_params`)

In `tools.py`, a function that reconciles both formats at execution time:

```python
def _merge_params(arguments: dict[str, Any]) -> dict[str, str]:
    params = dict(arguments.get("params") or {})
    additional = arguments.get("additionalProperties")
    if isinstance(additional, dict):
        for k, v in additional.items():
            params.setdefault(k, str(v))
    for key, value in arguments.items():
        if key not in {"resource_type", "params", "additionalProperties"}:
            params.setdefault(key, str(value))
    return params
```

Normalizes **three** distinct behaviors:

| LLM | Behavior | Example |
|-----|----------|---------|
| Anthropic/Llama | params in `params` | `{"resource_type": "Patient", "params": {"gender": "male"}}` |
| GPT-4o | params at top-level | `{"resource_type": "Patient", "gender": "male"}` |
| Qwen (schema leak) | params in `additionalProperties` | `{"resource_type": "Patient", "additionalProperties": {"birthdate": "le1964"}}` |

Precedence: `params` > `additionalProperties` > top-level (`setdefault` semantics).

### Additional fixes

- **Retry with exponential backoff** in both LLM clients (429, 503, 529). 4 retries, backoff 1→2→4→8s. Eliminated all rate limiting errors.
- **`suggested_query` in the planner**: the QueryPlan now includes a concrete suggested query. Injected into the executor system prompt. Helps all models, not just GPT-4o.

## Consequences

### Positive

- **Zero-change for Anthropic:** tool definitions, prompt, and schema that Claude receives are identical. No regression risk.
- **GPT-4o goes from ~53% to 100% on Simple.** The core tool calling problem is solved.
- **Extensible:** any future OpenAI-compatible provider (Mistral, etc.) benefits automatically.
- **The pattern is invisible:** no `if provider == "openai"` in the agent loop or tools. Adaptation happens in the serialization layer (llm.py) and deserialization layer (tools.py).

### Negative

- **Two representations of the same schema** coexist. Must remember that Anthropic and OpenAI schemas are different for the same tools.
- **`_merge_params` broadens the acceptance surface**: accepts params where the original schema wouldn't expect them. Deliberate but reduces strict validation.

### Risks

- If Anthropic changes its tool calling format, or OpenAI improves `additionalProperties` support, these adapters may become unnecessary. They're easy to remove.
- The planner generates `suggested_query` with Haiku — if Haiku changes behavior, it could generate incorrect queries. But the executor isn't obligated to follow them.

## Lesson Learned: Schema Leak in Qwen

### The incident

When implementing schema flattening, `_flatten_params_for_openai` promotes `additionalProperties` to the root level of the JSON schema. GPT-4o interprets it correctly as a JSON Schema directive. But **Qwen 3.5 9B interprets it as a field named `additionalProperties`** and generates:

```json
{"resource_type": "Patient", "additionalProperties": {"birthdate": "le1964-01-01"}}
```

### Root cause

Small models (9B params) don't have a robust distinction between JSON Schema *keywords* (`additionalProperties`, `type`, `required`) and user data fields. They see `additionalProperties` as "another field I can fill in."

### The fix

Instead of making flattening conditional per provider (fragile, couples business logic to transport), we normalize in `_merge_params`: if `additionalProperties` appears as a key in the arguments, we unpack its contents into the params dict.

### Derived rule

> **Any change to tool definitions, schema, or prompt must be validated against ALL benchmark models before considering the task complete.** A fix for one model can break another. The normalization layer (`_merge_params`) is the safe place to absorb differences — not the schema or the prompt.

## Alternatives Considered

### Option A: Improve tool descriptions with more examples
- **Tested:** added explicit examples of `gender`, `address-state`, `birthdate` in `count_fhir` description.
- **Result:** 0/7 improvement. GPT-4o ignores the `params` description if the schema doesn't force it to generate it.
- **Discarded:** the problem is schema-level, not documentation.

### Option B: Inject `suggested_query` in system prompt (no schema change)
- **Tested:** the planner generates `count_fhir('Patient', {'gender': 'male'})` injected as "Suggested query" in the prompt.
- **Result:** 2/7 improvement (inconsistent). GPT-4o sometimes follows the suggestion, sometimes not.
- **Partially adopted:** `suggested_query` was kept as a complement, but doesn't solve the problem alone.

### Option C: Explicit properties per filter (gender, address-state, etc.)
- Add `gender`, `address-state`, `birthdate` as named properties in the schema.
- **Discarded:** couples FHIR-specific knowledge to tool schemas. Doesn't scale with new resource types or search params.

### Option D: OpenAI `strict: true` (Structured Outputs)
- Forces the model to follow the schema exactly.
- **Incompatible:** `strict: true` prohibits `additionalProperties: true`, which is exactly what we need for dynamic search params.

### Option E: Aggressive prompt engineering ("NEVER call without params")
- **Discarded:** contaminates the prompt for all models, fragile, contradicts the principle that tools are self-documenting.

## Theoretical Framework

### Tool Calling as API Design

The `params: {additionalProperties: string}` pattern is the LLM tool calling equivalent of `**kwargs` in Python or `Record<string, string>` in TypeScript. It's an "escape hatch" for APIs with dynamic parameters.

This pattern works well when the model has prior experience with the API (Claude knows FHIR search params from training). It works poorly when the model treats the schema as a rigid specification (GPT-4o interprets "optional object with open keys" as "I probably don't need to fill this").

### Analogy with Adapter Pattern (GoF)

The solution follows the **Adapter Pattern**: the internal interface (tool definitions with `params`) remains canonical, and a per-provider adapter (`_flatten_params_for_openai`) translates to the representation each model understands best. `_merge_params` acts as a **normalizer** that unifies the different representations back to the internal format.

## References

- OpenAI Structured Outputs: `strict: true` prohibits `additionalProperties` — [OpenAI docs](https://platform.openai.com/docs/guides/structured-outputs)
- Anthropic tool use: supports `additionalProperties` natively — [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- FHIR Search params are dynamic by design — each resource type has its own set
- GoF Adapter Pattern: converts one class's interface into another that the client expects
