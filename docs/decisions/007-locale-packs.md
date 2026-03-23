# ADR-007: Locale Pack System

**Status:** Accepted

## Context

SaludAI had all Argentina-specific configuration hardcoded: terminology CSVs, Spanish system prompt, tool descriptions, terminology system enums. This prevents extending the agent to other LATAM countries without duplicating code.

We need a mechanism to package all locale-specific configuration in an extensible way without breaking the existing API.

## Decision

Implement a **locale pack** system using frozen dataclasses:

- `TerminologySystemDef`: defines a terminology system (key, URI, CSV, package)
- `LocalePack`: groups all configuration for a country/region (terminology, prompt, tool descriptions, enums)
- `load_locale_pack(code)`: factory that loads a pack by code (default: `"ar"`)
- Argentina (`"ar"`) ships as the only built-in pack
- CSVs live in `saludai_core/locales/ar/`

### Locale selection

- Environment variable `SALUDAI_LOCALE=ar` → `AgentConfig.locale` → `load_locale_pack("ar")`
- Default: `"ar"` — zero behavior change for existing users
- Future: discovery via `importlib.metadata.entry_points(group="saludai.locales")`

## Consequences

### Positive
- **Clear extensibility**: adding a new country means creating a new locale pack (no agent code changes)
- **Backward compatible**: AR as default, no changes to existing API
- **Immutable**: frozen dataclasses prevent accidental mutation
- **Demonstrable**: the README can showcase multi-country as a differentiating feature
- **Testable**: each pack is a constant that can be validated independently

### Negative
- Adding a new pack requires knowledge of the internal structure (mitigated with LOCALE_GUIDE.md)

### Risks
- If packs grow large (100+ concepts), import time could increase. Mitigable with lazy loading.

## Alternatives Considered

### 1. External YAML/JSON configuration
- Pros: no Python code required
- Cons: loses type safety, can't be bundled with the package, harder to validate

### 2. Subclasses / inheritance
- Pros: familiar OOP pattern
- Cons: overengineered for static data; makes testing more complex

### 3. Entry points from the start
- Pros: maximum extensibility
- Cons: premature abstraction — we don't have a second locale yet. Better to prepare the interface and activate entry points when there's real demand.
