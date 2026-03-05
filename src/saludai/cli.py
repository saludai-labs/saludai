"""SaludAI CLI — entry point for all SaludAI commands."""

from __future__ import annotations

import sys


def main() -> None:
    """Run SaludAI CLI commands.

    Usage:
        saludai mcp     — Start the MCP server (stdio transport)
        saludai version — Show version
    """
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print("Usage: saludai <command>")
        print()
        print("Commands:")
        print("  mcp       Start the MCP server (stdio transport)")
        print("  version   Show version information")
        print()
        print("Options:")
        print("  --help    Show this message")
        sys.exit(0)

    command = args[0]

    if command == "version":
        from saludai import __version__

        print(f"saludai {__version__}")

    elif command == "mcp":
        from saludai_mcp.server import main as mcp_main

        mcp_main()

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'saludai --help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
