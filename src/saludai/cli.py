"""SaludAI CLI — entry point for all SaludAI commands."""

from __future__ import annotations

import sys


def main() -> None:
    """Run SaludAI CLI commands.

    Usage:
        saludai mcp              — Start the MCP server (stdio transport)
        saludai query "pregunta" — Ask a question to the FHIR agent
        saludai serve            — Start the REST API server
        saludai version          — Show version
    """
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print("Usage: saludai <command> [args]")
        print()
        print("Commands:")
        print("  mcp                Start the MCP server (stdio transport)")
        print('  query "pregunta"   Ask a question to the FHIR agent')
        print("  serve              Start the REST API server")
        print("  version            Show version information")
        print()
        print("Environment variables:")
        print(
            "  SALUDAI_FHIR_SERVER_URL    FHIR R4 server URL (default: http://localhost:8080/fhir)"
        )
        print("  SALUDAI_FHIR_AUTH_TYPE     Auth type: none, bearer (default: none)")
        print("  SALUDAI_FHIR_AUTH_TOKEN    Bearer token for FHIR auth")
        print("  SALUDAI_LLM_PROVIDER       LLM provider: anthropic, openai, ollama")
        print("  SALUDAI_LLM_MODEL          Model name (default: claude-sonnet-4-20250514)")
        print("  SALUDAI_LLM_API_KEY        API key for the LLM provider")
        print("  SALUDAI_LOCALE             Locale pack: ar (default: ar)")
        sys.exit(0)

    command = args[0]

    if command == "version":
        from saludai import __version__

        print(f"saludai {__version__}")

    elif command == "mcp":
        from saludai_mcp.server import main as mcp_main

        mcp_main()

    elif command == "query":
        _run_query(args[1:])

    elif command == "serve":
        _run_serve(args[1:])

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'saludai --help' for usage.", file=sys.stderr)
        sys.exit(1)


def _run_query(args: list[str]) -> None:
    """Run a single query through the agent loop."""
    if not args:
        print('Usage: saludai query "your question here"', file=sys.stderr)
        sys.exit(1)

    query = " ".join(args)

    import asyncio

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    asyncio.run(_execute_query(query))


async def _execute_query(query: str) -> None:
    """Set up the agent and run a query."""
    from saludai_agent.config import AgentConfig
    from saludai_agent.llm import create_llm_client
    from saludai_agent.loop import AgentLoop
    from saludai_agent.tracing import create_tracer
    from saludai_core.config import FHIRConfig
    from saludai_core.fhir_client import FHIRClient
    from saludai_core.locales import load_locale_pack
    from saludai_core.terminology import TerminologyResolver

    agent_cfg = AgentConfig()
    fhir_cfg = FHIRConfig()

    if not agent_cfg.llm_api_key:
        print(
            "Error: SALUDAI_LLM_API_KEY is required (or ANTHROPIC_API_KEY / OPENAI_API_KEY).",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        locale_pack = load_locale_pack(agent_cfg.locale)
    except Exception:
        locale_pack = None

    terminology = TerminologyResolver(locale_pack=locale_pack)
    llm = create_llm_client(agent_cfg)
    tracer = create_tracer(agent_cfg)

    async with FHIRClient(config=fhir_cfg) as fhir_client:
        agent = AgentLoop(
            llm=llm,
            fhir_client=fhir_client,
            terminology_resolver=terminology,
            config=agent_cfg,
            tracer=tracer,
            locale_pack=locale_pack,
        )
        result = await agent.run(query)

    print(result.answer)
    if result.trace_url:
        print(f"\nTrace: {result.trace_url}", file=sys.stderr)


def _run_serve(args: list[str]) -> None:
    """Start the FastAPI REST API server."""
    import uvicorn

    host = "0.0.0.0"
    port = 8000

    # Simple arg parsing for --host and --port
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    uvicorn.run("saludai_api.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
