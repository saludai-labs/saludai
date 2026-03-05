# SaludAI

**The most precise FHIR agent for Latin America** — benchmarked against FHIR-AgentBench, with full observability, designed for public health systems.

[![CI](https://github.com/saludai-labs/saludai/actions/workflows/ci.yml/badge.svg)](https://github.com/saludai-labs/saludai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## What is SaludAI?

SaludAI is an AI agent that understands clinical queries in natural language, translates them into FHIR R4 API calls, and returns accurate, traceable answers. Built specifically for Latin American health systems, it handles SNOMED CT (Argentine edition), CIE-10, and LOINC terminology out of the box.

Ask: *"Pacientes con diabetes tipo 2 mayores de 60 en Buenos Aires"*
Get: A structured, sourced answer with full Langfuse tracing of every step.

## Benchmark

SaludAI is evaluated against a custom FHIR-AgentBench inspired by [Verily/KAIST/MIT FHIR-AgentBench](https://arxiv.org/abs/2408.01693), adapted for Argentine clinical data.

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

**Sprint 3 (Precision) — Complete.** The project currently provides:

- UV monorepo with 4 packages (core, agent, mcp, api)
- Docker Compose setup with HAPI FHIR R4 + 536 synthetic Argentine clinical resources
- Async FHIR client (`saludai-core`) with connection, search, and read operations
- Terminology resolver (SNOMED CT AR, CIE-10, LOINC) with fuzzy matching
- FHIR query builder with fluent API
- Agent loop with LLM tool calling (provider-agnostic: Anthropic/OpenAI/Ollama)
- 5 tools: resolve_terminology, search_fhir, get_resource, execute_code (sandboxed Python)
- Locale packs for multi-country support (Argentina built-in)
- Full Langfuse tracing integration
- FHIR-AgentBench evaluation framework (50 questions, hybrid LLM-as-judge)
- GitHub Actions CI with Ruff linting, Pytest, and coverage (84.57%)
- 375+ passing tests (unit + integration)

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
docs/               # Architecture, roadmap, ADRs
```

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

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
