"""SaludAI MCP — MCP server for Claude Desktop and other agents."""

__version__ = "0.1.0"

from saludai_mcp.config import MCPConfig
from saludai_mcp.server import main, mcp

__all__ = ["MCPConfig", "main", "mcp"]
