"""Tests for the SaludAI MCP server."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from saludai_mcp.config import MCPConfig
from saludai_mcp.server import mcp

# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestMCPConfig:
    """Tests for MCPConfig defaults and env loading."""

    def test_defaults(self) -> None:
        cfg = MCPConfig()
        assert cfg.fhir_server_url == "http://localhost:8080/fhir"
        assert cfg.fhir_timeout == 30.0
        assert cfg.locale == "ar"
        assert cfg.mcp_server_name == "saludai"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_FHIR_SERVER_URL", "http://custom:9090/fhir")
        monkeypatch.setenv("SALUDAI_LOCALE", "cl")
        cfg = MCPConfig()
        assert cfg.fhir_server_url == "http://custom:9090/fhir"
        assert cfg.locale == "cl"


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Tests that tools are registered correctly on the FastMCP server."""

    def test_server_name(self) -> None:
        assert mcp.name == "saludai"

    def test_four_tools_registered(self) -> None:
        tools = mcp._tool_manager.list_tools()
        names = {t.name for t in tools}
        assert names == {"resolve_terminology", "search_fhir", "get_resource", "run_python"}

    def test_resolve_terminology_schema(self) -> None:
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        tool = tools["resolve_terminology"]
        schema = tool.parameters
        assert "term" in schema["properties"]
        assert "term" in schema.get("required", [])

    def test_search_fhir_schema(self) -> None:
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        tool = tools["search_fhir"]
        schema = tool.parameters
        assert "resource_type" in schema["properties"]
        assert "params" in schema["properties"]

    def test_get_resource_schema(self) -> None:
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        tool = tools["get_resource"]
        schema = tool.parameters
        assert "resource_type" in schema["properties"]
        assert "resource_id" in schema["properties"]

    def test_run_python_schema(self) -> None:
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}
        tool = tools["run_python"]
        schema = tool.parameters
        assert "code" in schema["properties"]


# ---------------------------------------------------------------------------
# Tool execution tests (mocked dependencies)
# ---------------------------------------------------------------------------


class TestRunPython:
    """Tests for the run_python tool (no external deps needed)."""

    @pytest.mark.anyio()
    async def test_simple_print(self) -> None:
        result = await mcp.call_tool("run_python", {"code": "print(2 + 2)"})
        text = _extract_text(result)
        assert "4" in text

    @pytest.mark.anyio()
    async def test_empty_code(self) -> None:
        result = await mcp.call_tool("run_python", {"code": ""})
        text = _extract_text(result)
        assert "no code" in text.lower()

    @pytest.mark.anyio()
    async def test_forbidden_import(self) -> None:
        result = await mcp.call_tool("run_python", {"code": "import os"})
        text = _extract_text(result)
        assert "not allowed" in text.lower() or "error" in text.lower()


class TestResolveTerminology:
    """Tests for resolve_terminology tool with mocked resolver."""

    @pytest.mark.anyio()
    async def test_resolver_not_configured(self) -> None:
        """When _terminology_resolver is None, returns error JSON."""
        import saludai_mcp.server as srv

        original = srv._terminology_resolver
        srv._terminology_resolver = None
        try:
            result = await mcp.call_tool("resolve_terminology", {"term": "diabetes"})
            text = _extract_text(result)
            assert "error" in text.lower()
        finally:
            srv._terminology_resolver = original

    @pytest.mark.anyio()
    async def test_resolve_with_mock(self) -> None:
        """Calls execute_resolve_terminology with correct arguments."""
        import saludai_mcp.server as srv

        mock_resolver = object()  # sentinel
        original = srv._terminology_resolver
        srv._terminology_resolver = mock_resolver
        try:
            with patch(
                "saludai_mcp.server.execute_resolve_terminology",
                return_value='{"code": "44054006", "display": "Diabetes mellitus type 2"}',
            ) as mock_exec:
                result = await mcp.call_tool(
                    "resolve_terminology",
                    {"term": "diabetes tipo 2", "system": "snomed_ct"},
                )
                mock_exec.assert_called_once_with(
                    mock_resolver,
                    {"term": "diabetes tipo 2", "system": "snomed_ct"},
                )
                text = _extract_text(result)
                assert "44054006" in text
        finally:
            srv._terminology_resolver = original


class TestSearchFhir:
    """Tests for search_fhir tool with mocked FHIR client."""

    @pytest.mark.anyio()
    async def test_client_not_configured(self) -> None:
        import saludai_mcp.server as srv

        original = srv._fhir_client
        srv._fhir_client = None
        try:
            result = await mcp.call_tool("search_fhir", {"resource_type": "Patient"})
            text = _extract_text(result)
            assert "error" in text.lower()
        finally:
            srv._fhir_client = original

    @pytest.mark.anyio()
    async def test_search_with_mock(self) -> None:
        import saludai_mcp.server as srv

        mock_client = AsyncMock()
        original = srv._fhir_client
        srv._fhir_client = mock_client
        try:
            with patch(
                "saludai_mcp.server.execute_search_fhir",
                return_value="Found 5 resources (5 Patient).",
            ) as mock_exec:
                result = await mcp.call_tool(
                    "search_fhir",
                    {"resource_type": "Patient", "params": {"name": "Garcia"}},
                )
                mock_exec.assert_called_once_with(
                    mock_client,
                    {"resource_type": "Patient", "params": {"name": "Garcia"}},
                )
                text = _extract_text(result)
                assert "5" in text
        finally:
            srv._fhir_client = original


class TestGetResource:
    """Tests for get_resource tool with mocked FHIR client."""

    @pytest.mark.anyio()
    async def test_client_not_configured(self) -> None:
        import saludai_mcp.server as srv

        original = srv._fhir_client
        srv._fhir_client = None
        try:
            result = await mcp.call_tool(
                "get_resource",
                {"resource_type": "Patient", "resource_id": "123"},
            )
            text = _extract_text(result)
            assert "error" in text.lower()
        finally:
            srv._fhir_client = original

    @pytest.mark.anyio()
    async def test_get_with_mock(self) -> None:
        import saludai_mcp.server as srv

        mock_client = AsyncMock()
        original = srv._fhir_client
        srv._fhir_client = mock_client
        try:
            with patch(
                "saludai_mcp.server.execute_get_resource",
                return_value="Patient/123 | name=Juan Garcia",
            ) as mock_exec:
                result = await mcp.call_tool(
                    "get_resource",
                    {"resource_type": "Patient", "resource_id": "123"},
                )
                mock_exec.assert_called_once_with(
                    mock_client,
                    {"resource_type": "Patient", "resource_id": "123"},
                )
                text = _extract_text(result)
                assert "Juan Garcia" in text
        finally:
            srv._fhir_client = original


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_text(result: Any) -> str:
    """Extract text content from MCP call_tool result."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return str(result)
    # Sequence of ContentBlock
    parts = []
    for block in result:
        if hasattr(block, "text"):
            parts.append(block.text)
        else:
            parts.append(str(block))
    return "\n".join(parts)
