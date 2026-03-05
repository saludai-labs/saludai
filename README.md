# SaludAI

**The most precise FHIR agent for Latin America** — benchmarked against FHIR-AgentBench, with full observability, designed for public health systems.

[![CI](https://github.com/saludai-labs/saludai/actions/workflows/ci.yml/badge.svg)](https://github.com/saludai-labs/saludai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Benchmark: 98%](https://img.shields.io/badge/FHIR--AgentBench-98%25-brightgreen)](docs/experiments/EXPERIMENTS.md)
[![Coverage: 84.57%](https://img.shields.io/badge/Coverage-84.57%25-green)](.github/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)

## What is SaludAI?

SaludAI is an AI agent that understands clinical queries in natural language, translates them into FHIR R4 API calls, and returns accurate, traceable answers. Built specifically for Latin American health systems, it handles SNOMED CT (Argentine edition), CIE-10, and LOINC terminology out of the box.

Ask: *"Pacientes con diabetes tipo 2 mayores de 60 en Buenos Aires"*
Get: A structured, sourced answer with full Langfuse tracing of every step.

## Benchmark

SaludAI is evaluated against a custom FHIR-AgentBench inspired by [Verily/KAIST/MIT FHIR-AgentBench](https://arxiv.org/abs/2509.19319) ([repo](https://github.com/glee4810/FHIR-AgentBench)), adapted for Argentine clinical data.

| Model | Accuracy | Simple (8) | Medium (20) | Complex (22) | Avg Duration |
|-------|----------|------------|-------------|--------------|-------------|
| Claude Sonnet 4.5 | **98.0%** | 8/8 (100%) | 20/20 (100%) | 21/22 (95%) | 34.6s |

*Evaluated on 50 questions against 536 synthetic Argentine clinical resources (5 FHIR types: Patient, Condition, Observation, MedicationRequest, Encounter). LLM-as-judge scoring with hybrid programmatic + Claude Haiku. See [docs/experiments/EXPERIMENTS.md](docs/experiments/EXPERIMENTS.md) for full methodology.*

```bash
# Run the benchmark
docker compose up -d
uv run python -m benchmarks.run_eval

# Run a specific category
uv run python -m benchmarks.run_eval --category simple
```

## Current Status

The project provides:

- UV monorepo with 4 packages (core, agent, mcp, api)
- Docker Compose setup with HAPI FHIR R4 + 536 synthetic Argentine clinical resources
- Async FHIR client (`saludai-core`) with connection, search, and read operations
- Terminology resolver (SNOMED CT AR, CIE-10, LOINC) with fuzzy matching
- FHIR query builder with fluent API
- Agent loop with LLM tool calling (provider-agnostic: Anthropic/OpenAI/Ollama)
- 5 tools: resolve_terminology, search_fhir, get_resource, execute_code (sandboxed Python)
- **MCP server** (`saludai-mcp`) — connect from Claude Desktop, Claude Code, Cursor, or any MCP client
- **REST API** (`saludai-api`) — FastAPI server with `/query` endpoint
- **CLI** — `saludai query`, `saludai serve`, `saludai mcp`
- Locale packs for multi-country support (Argentina built-in)
- Full Langfuse tracing integration
- FHIR-AgentBench evaluation framework (50 questions, hybrid LLM-as-judge)
- GitHub Actions CI with Ruff linting, Pytest, and coverage (84.57%)
- 473 passing tests (unit + integration)

## Quick Start

```bash
# Clone and install
git clone https://github.com/saludai-labs/saludai.git
cd saludai
uv sync

# Start HAPI FHIR with synthetic Argentine data
docker compose up -d

# Verify FHIR server is running (wait ~30s for seeding)
curl http://localhost:8080/fhir/Patient?_count=5

# Run tests
uv run pytest
```

**Prerequisites:** Python 3.12+, [UV](https://docs.astral.sh/uv/), Docker

## Project Structure

```
packages/
  saludai-core/     # FHIR client, terminology resolver, shared types
  saludai-agent/    # Self-reasoning loop + tools
  saludai-mcp/      # MCP server for Claude Desktop / agents
  saludai-api/      # FastAPI REST interface
data/seed/          # Synthetic Argentine patient data (Synthea-style)
benchmarks/         # FHIR-AgentBench evaluation scripts
notebooks/          # Interactive Jupyter demos
docs/               # Architecture, roadmap, ADRs
```

## MCP Server

SaludAI exposes its tools via the [Model Context Protocol](https://modelcontextprotocol.io), compatible with Claude Desktop, Claude Code, Cursor, and any MCP client.

```bash
# Start FHIR server first
docker compose up -d

# Run the MCP server (stdio transport)
uv run saludai-mcp
```

**Claude Desktop / Claude Code config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "saludai": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/saludai", "saludai-mcp"],
      "env": {
        "SALUDAI_FHIR_SERVER_URL": "http://localhost:8080/fhir"
      }
    }
  }
}
```

**Available tools:** `resolve_terminology`, `search_fhir`, `get_resource`, `run_python`

## Locale Packs — Multi-Country Support

SaludAI supports country/region-specific configuration through **locale packs**. A locale pack bundles terminology data, system prompts, and tool descriptions for a specific health system.

Argentina (`ar`) comes built-in as the default:

```python
from saludai_core.locales import load_locale_pack

pack = load_locale_pack("ar")  # SNOMED CT AR, CIE-10 AR, LOINC
```

To switch locale via environment variable:

```bash
export SALUDAI_LOCALE=ar  # default
```

Creating a new locale pack for your country is straightforward — see [docs/LOCALE_GUIDE.md](docs/LOCALE_GUIDE.md) for the full guide.

## Notebooks

Interactive Jupyter notebooks to explore SaludAI's capabilities:

| Notebook | Description |
|----------|-------------|
| [01-getting-started](notebooks/01-getting-started.ipynb) | FHIR client, terminology resolver, query builder |
| [02-agent-queries](notebooks/02-agent-queries.ipynb) | Natural language queries with the agent loop |
| [03-benchmark-eval](notebooks/03-benchmark-eval.ipynb) | Run and analyze the FHIR-AgentBench evaluation |

```bash
# Run notebooks
uv run jupyter notebook notebooks/
```

## CLI & REST API

SaludAI provides a unified CLI and a REST API for programmatic access:

```bash
# Query the agent from the terminal
uv run saludai query "Pacientes con diabetes tipo 2 mayores de 60"

# Start the REST API server
uv run saludai serve
# POST http://localhost:8000/query {"query": "..."}

# Start the MCP server
uv run saludai mcp
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
