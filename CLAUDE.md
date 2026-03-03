# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SaludAI — Claude Code Instructions

> **Read this file completely before any task.** This is your operating manual.

## Current State

**This project is in pre-development (documentation/planning phase).** Check `docs/PROGRESS.md` for the latest state before doing anything. All documentation is written in Spanish.

## Identity

SaludAI is the most precise FHIR agent for Latin America — benchmarked against FHIR-AgentBench, with full observability, designed for public health systems.

**Long-term vision:** A modular AI platform (5 modules) that transforms how public health systems in LATAM interact with clinical data. Module 1 (FHIR Smart Agent) is the open-source foundation everything else builds on.

**Current stage:** Etapa 1 — Module 1 (FHIR Smart Agent). See `docs/ROADMAP.md` for details.

---

## Project Structure (Target)

> **Note:** This is the planned structure. As of project inception, only `CLAUDE.md`, `docs/`, and `tasks/` exist on disk. Verify what actually exists before referencing any path.

```
saludai/
├── CLAUDE.md                    # YOU ARE HERE
├── pyproject.toml               # UV workspace root
├── docker-compose.yml           # HAPI FHIR + Langfuse + agent
├── README.md                    # Public-facing, with benchmark badges
├── packages/
│   ├── saludai-core/            # FHIR client, terminology resolver, shared types
│   │   ├── pyproject.toml
│   │   ├── src/saludai_core/
│   │   └── tests/
│   ├── saludai-agent/           # Self-reasoning loop + tools
│   │   ├── pyproject.toml
│   │   ├── src/saludai_agent/
│   │   └── tests/
│   ├── saludai-mcp/             # MCP server for Claude Desktop / agents
│   │   ├── pyproject.toml
│   │   ├── src/saludai_mcp/
│   │   └── tests/
│   └── saludai-api/             # FastAPI REST interface
│       ├── pyproject.toml
│       ├── src/saludai_api/
│       └── tests/
├── benchmarks/                  # FHIR-AgentBench eval scripts + results
├── notebooks/                   # Jupyter demos (clinical, epi, benchmark)
├── docs/
│   ├── ROADMAP.md               # Sprint-by-sprint execution plan
│   ├── ARCHITECTURE.md          # Technical architecture decisions
│   ├── PROGRESS.md              # Current session state
│   ├── CHANGELOG.md             # What changed per session
│   └── decisions/               # ADRs (Architecture Decision Records)
│       └── 000-template.md
├── tasks/
│   ├── todo.md                  # Current session tasks (checkable)
│   ├── backlog.md               # Future ideas — NOT for this sprint
│   └── lessons.md               # Patterns learned from mistakes
└── .github/workflows/           # CI: lint + test + benchmark
```

---

## Workflow Rules

### 1. Plan Before Code
- Enter **plan mode** for ANY task with 3+ steps or architectural impact.
- Write the plan to `tasks/todo.md` with checkable items BEFORE coding.
- If something goes sideways: **STOP → re-plan → don't push through**.
- For trivial fixes (typos, single-line changes): just do it.

### 2. Scope Discipline
- **If it's not in `docs/ROADMAP.md` for the current sprint, it goes to `tasks/backlog.md`.**
- Never add features from Modules 2-5 to Module 1. The temptation will be strong. Resist.
- When you spot something that "would be nice to have": add it to backlog, move on.

### 3. Session Protocol
```
START OF SESSION:
1. Read `docs/PROGRESS.md` → know where we left off
2. Read `tasks/lessons.md` → don't repeat mistakes
3. Read current sprint in `docs/ROADMAP.md` → know today's target
4. Update `tasks/todo.md` with session plan

END OF SESSION:
1. Update `docs/PROGRESS.md` with current state
2. Update `docs/CHANGELOG.md` with what changed
3. If any architectural decision was made → create ADR in `docs/decisions/`
4. Commit with conventional commits
```

### 4. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern.
- Write rules for yourself that prevent the same mistake.
- Review lessons at session start.

### 5. Verification Before Done
- Never mark a task complete without proving it works.
- Run `uv run pytest` — tests MUST pass.
- Run `uv run ruff check` — no lint errors.
- Ask yourself: **"Would a staff engineer approve this PR?"**
- For agent features: show a working query with trace in Langfuse.

### 6. Subagent Strategy
- Use subagents for research, exploration, and parallel analysis.
- Keep main context window clean — offload heavy reading to subagents.
- One task per subagent for focused execution.

---

## Technical Standards

### Python
- **Version:** 3.12+
- **Package manager:** UV (not pip, not poetry)
- **Linting:** Ruff (replaces black + isort + flake8)
- **Type checking:** Strict. All public functions have type hints. Use `from __future__ import annotations`.
- **Testing:** Pytest. Minimum 70% coverage target. Use fixtures, not mocks when possible.
- **Naming:** snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants.
- **Imports:** Absolute imports only (`from saludai_core.fhir import FHIRClient`, never relative).
- **Docstrings:** Google style. Required on all public functions and classes.
- **Error handling:** Custom exception hierarchy in `saludai_core.exceptions`. Never bare `except:`.

### Code Quality Rules
- **No LangChain.** The agent loop is custom — simpler, auditable, traceable.
- **No global state.** Dependency injection via constructors.
- **No magic strings.** Use enums or constants for FHIR resource types, search parameters, etc.
- **Fail fast.** Validate inputs at boundaries. Use Pydantic models for all external data.
- **Log, don't print.** Use `structlog` for structured logging. Every significant operation logs.

### FHIR Specifics
- **FHIR R4** only (no R5, no DSTU2). This matches HAPI FHIR and Argentina's ecosystem.
- **Terminology:** SNOMED CT Argentine edition, CIE-10 (Argentine adaptation), LOINC.
- **Profiles:** openRSD (Argentina's national FHIR profiles) when relevant.
- **Client library:** `fhir.resources` for models, `httpx` for HTTP (async-first).
- **Never hardcode FHIR server URLs.** Always configurable via environment.

### LLM Integration
- **Provider-agnostic.** Abstract behind a `LLMClient` interface.
- **Supported:** Anthropic (Claude), OpenAI, Ollama (local).
- **Development:** Use Ollama with small models for fast iteration.
- **Benchmarks/eval:** Use Claude Sonnet for reproducibility.
- **Always pass `temperature=0`** for deterministic agent behavior in evals.
- **All LLM calls go through Langfuse** for tracing. No exceptions.

### Docker
- **docker-compose.yml** must work with `docker compose up` — no manual steps.
- **Services:** HAPI FHIR (R4), Langfuse, PostgreSQL (for Langfuse), agent API.
- **Health checks** on all services.
- **Named volumes** for persistence.

### Git
- **Conventional commits:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- **Branch per sprint:** `sprint/01-foundation`, `sprint/02-agent-brain`, etc.
- **Main is always deployable.** Merge only when CI is green.
- **Never commit secrets.** `.env.example` with dummy values, `.env` in `.gitignore`.

---

## Architecture Decisions

Architectural decisions are logged in `docs/decisions/` as ADRs (Architecture Decision Records).

**To create a new ADR:**
1. Copy `docs/decisions/000-template.md`
2. Number sequentially: `001-monorepo-structure.md`, `002-no-langchain.md`, etc.
3. Fill in: Context, Decision, Consequences, Alternatives Considered
4. Reference from `docs/ARCHITECTURE.md` if it affects overall design

**Key decisions already made:**
- ADR-001: Monorepo with UV workspaces (`docs/decisions/001-monorepo-uv-workspaces.md`)
- ADR-002: No LangChain — custom agent loop for auditability (referenced in CLAUDE.md, ADR file not yet created)
- ADR-003: Python-first with strategic polyglot (`docs/decisions/003-python-first-polyglot.md`)
- ADR-004: Langfuse for observability (referenced in CLAUDE.md, ADR file not yet created)
- ADR-005: FHIR R4 only (referenced in CLAUDE.md, ADR file not yet created)

---

## Domain Knowledge

### What is FHIR?
FHIR (Fast Healthcare Interoperability Resources) is the standard for healthcare data exchange. Resources are JSON objects (Patient, Condition, Observation, MedicationRequest, etc.) connected by references.

### What is the agent doing?
User says: "Pacientes con diabetes tipo 2 mayores de 60 en Buenos Aires"
Agent must:
1. Resolve "diabetes tipo 2" → SNOMED CT code 44054006
2. Build FHIR query: `GET /Condition?code=44054006&_include=Condition:subject`
3. Filter patients by age (calculated from birthDate) and province
4. Follow references: Condition → Patient → check demographics
5. Return narrative answer with sources

### What makes this hard?
- Terminology mapping is ambiguous (fuzzy matching needed)
- References between resources require multi-hop traversal
- FHIR search API is powerful but complex (chained params, _include, _revinclude)
- LLMs hallucinate medical codes — pre-validation is mandatory
- Results need to be traced for clinical auditability

---

## Quick Commands

```bash
# Setup
uv sync                              # Install all dependencies
docker compose up -d                  # Start HAPI FHIR + Langfuse

# Development
uv run pytest                         # Run all tests
uv run pytest packages/saludai-core/  # Run core tests only
uv run pytest path/to/test_file.py::test_name  # Run a single test
uv run ruff check .                   # Lint
uv run ruff format .                  # Format

# Benchmarks
uv run python benchmarks/run_eval.py  # Run FHIR-AgentBench evaluation

# MCP Server
uv run saludai-mcp serve              # Start MCP server locally
```

---

## Current Sprint Reference

**Always check `docs/PROGRESS.md`** for the latest state. But as a quick reference:

- **Sprint 1:** Foundation (repos, Docker, Synthea, FHIR client)
- **Sprint 2:** Agent brain (terminology, query builder, agent loop, Langfuse)
- **Sprint 3:** Precision (multi-turn, reference nav, code interpreter, benchmark improvement)
- **Sprint 4:** Product (MCP server, API, PyPI, notebooks, blog, video)

See `docs/ROADMAP.md` for session-by-session breakdown.
