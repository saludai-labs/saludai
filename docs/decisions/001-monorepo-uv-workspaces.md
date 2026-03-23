# ADR-001: Monorepo with UV Workspaces

**Status:** Accepted

## Context

SaludAI has 4 packages (core, agent, mcp, api) that share types, configuration, and infrastructure. We need to decide whether they go in separate repos or a monorepo.

## Decision

Monorepo with UV workspaces. All Python packages live under `packages/` in a single repository.

## Consequences

### Positive
- Cross-package changes in a single PR (e.g., change a type in core and update agent)
- Unified CI — one pipeline tests everything
- Atomic refactors without coordinating across repos
- `uv sync` installs the entire workspace at once

### Negative
- CI gets slower as the repo grows (mitigable with path filtering)
- An issue in one package can block CI for all
- PyPI publishing requires per-package scripts

### Risks
- If the monorepo grows significantly (+10 packages), CI complexity may become a problem.

## Alternatives Considered

### Multi-repo (one repo per package)
- Pros: independent CI, independent releases, more familiar for contributors
- Cons: cross-package changes require multiple coordinated PRs; versioning hell; complex local setup

### Multi-repo with Git submodules
- Pros: groups without coupling
- Cons: submodules are notoriously fragile; unnecessary complexity for 4 packages
