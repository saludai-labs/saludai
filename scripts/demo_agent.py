"""Demo: run the SaludAI agent loop against a live HAPI FHIR server.

Usage:
    uv run python scripts/demo_agent.py "Pacientes con diabetes tipo 2"
    uv run python scripts/demo_agent.py "¿Cuántos pacientes hay en Buenos Aires?"
    uv run python scripts/demo_agent.py "Buscar observaciones de glucosa en sangre"
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from saludai_agent.config import AgentConfig
from saludai_agent.llm import create_llm_client
from saludai_agent.loop import AgentLoop
from saludai_agent.tracing import create_tracer
from saludai_core.fhir_client import FHIRClient
from saludai_core.terminology import TerminologyResolver


async def main(query: str) -> None:
    """Run a single agent query and print the result."""
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    config = AgentConfig()

    print(f"Provider: {config.llm_provider}")
    print(f"Model:    {config.llm_model}")
    print(f"API key:  {'***' + config.llm_api_key[-4:] if config.llm_api_key else 'NOT SET'}")
    print(f"Langfuse: {'enabled' if config.langfuse_enabled else 'disabled'}")
    print(f"Query:    {query}")
    print("-" * 60)

    llm = create_llm_client(config)
    resolver = TerminologyResolver()
    tracer = create_tracer(config)

    async with FHIRClient() as fhir_client:
        loop = AgentLoop(
            llm=llm,
            fhir_client=fhir_client,
            terminology_resolver=resolver,
            config=config,
            tracer=tracer,
        )

        result = await loop.run(query)

    tracer.flush()

    print(f"\nSuccess:    {result.success}")
    print(f"Iterations: {result.iterations}")
    print(f"Tool calls: {len(result.tool_calls_made)}")
    for tc in result.tool_calls_made:
        print(f"  - {tc.name}({tc.arguments})")
    if result.trace_id:
        print(f"Trace ID:   {result.trace_id}")
    if result.trace_url:
        print(f"Trace URL:  {result.trace_url}")
    print("-" * 60)
    print(f"\n{result.answer}")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Pacientes con diabetes tipo 2"
    asyncio.run(main(query))
