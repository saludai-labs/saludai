# SaludAI

**The most precise FHIR agent for Latin America** — benchmarked against FHIR-AgentBench, with full observability, designed for public health systems.

[![CI](https://github.com/saludai-labs/saludai/actions/workflows/ci.yml/badge.svg)](https://github.com/saludai-labs/saludai/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## What is SaludAI?

SaludAI is an AI agent that understands clinical queries in natural language, translates them into FHIR R4 API calls, and returns accurate, traceable answers. Built specifically for Latin American health systems, it handles SNOMED CT (Argentine edition), CIE-10, and LOINC terminology out of the box.

Ask: *"Pacientes con diabetes tipo 2 mayores de 60 en Buenos Aires"*
Get: A structured, sourced answer with full Langfuse tracing of every step.

## Current Status

**Sprint 1 (Foundation) — Complete.** The project currently provides:

- UV monorepo with 4 packages (core, agent, mcp, api)
- Docker Compose setup with HAPI FHIR R4 + 55 synthetic Argentine patients
- Async FHIR client (`saludai-core`) with connection, search, and read operations
- GitHub Actions CI with Ruff linting and Pytest
- 18 passing tests (unit + integration)

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
uv run pytest packages/saludai-core/
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

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
