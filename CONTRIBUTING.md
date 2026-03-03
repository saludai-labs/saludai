# Contributing to SaludAI

Thanks for your interest in contributing to SaludAI! This guide covers everything you need to get started.

For an overview of the project, see [README.md](README.md).

## Prerequisites

- **Python 3.12+**
- **[UV](https://docs.astral.sh/uv/)** — package manager (not pip, not poetry)
- **Docker** and **Docker Compose** — for HAPI FHIR server
- **Git** with conventional commit knowledge

## Development Setup

```bash
# Clone the repository
git clone https://github.com/saludai-labs/saludai.git
cd saludai

# Install all dependencies (including dev tools)
uv sync

# Start HAPI FHIR R4 with synthetic data
docker compose up -d

# Install pre-commit hooks
uv run pre-commit install

# Verify everything works
uv run ruff check .
uv run pytest packages/saludai-core/
```

## Code Style

We use **Ruff** for linting and formatting (replaces black + isort + flake8).

- **Type hints** on all public functions — use `from __future__ import annotations`
- **Google-style docstrings** on all public functions and classes
- **Absolute imports only** — `from saludai_core.fhir_client import FHIRClient`, never relative
- **snake_case** for functions/variables, **PascalCase** for classes, **UPPER_SNAKE** for constants
- **No bare `except:`** — use the custom exception hierarchy in `saludai_core.exceptions`
- **No global state** — dependency injection via constructors
- **structlog** for logging — never `print()`

```bash
# Check linting
uv run ruff check .

# Auto-format
uv run ruff format .
```

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use for |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Adding or updating tests |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `chore:` | Build process, CI, dependencies |

Examples:
```
feat: add terminology resolver for SNOMED CT
fix: handle missing total in FHIR search bundles
docs: update roadmap with sprint 2 sessions
test: add integration tests for FHIR client read
```

## Testing

We use **Pytest** with two categories of tests:

```bash
# Run all tests (unit only — no external services needed)
uv run pytest

# Run a specific package
uv run pytest packages/saludai-core/

# Run integration tests (requires HAPI FHIR running)
uv run pytest -m integration

# Run a single test
uv run pytest packages/saludai-core/tests/test_fhir_client.py::test_search_patients
```

Integration tests are marked with `@pytest.mark.integration` and skip automatically if HAPI FHIR is not running.

## Pull Request Process

1. **Create a branch** from `main` with a descriptive name
2. **Make your changes** following the code style above
3. **Add tests** for any new functionality
4. **Run checks** before pushing:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest
   ```
5. **Open a PR** with a clear description of what and why
6. CI must pass (Ruff + Pytest) before merge

## Project Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical architecture and [docs/decisions/](docs/decisions/) for Architecture Decision Records (ADRs).

Key architectural constraints:
- **FHIR R4 only** — no R5, no DSTU2
- **No LangChain** — custom agent loop for auditability
- **Provider-agnostic LLM** — Anthropic, OpenAI, Ollama all supported
- **All LLM calls traced** through Langfuse

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. A formal Code of Conduct will be published soon. In the meantime, please be respectful and constructive in all interactions.
