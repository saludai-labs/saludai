"""MCP server configuration via pydantic-settings.

Settings are loaded from environment variables with the ``SALUDAI_`` prefix,
reusing the same convention as ``saludai_core`` and ``saludai_agent``.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPConfig(BaseSettings):
    """Configuration for the SaludAI MCP server.

    Attributes:
        fhir_server_url: Base URL of the FHIR R4 server.
        fhir_auth_type: Authentication method (``"none"`` or ``"bearer"``).
        fhir_auth_token: Bearer token when ``fhir_auth_type`` is ``"bearer"``.
        fhir_timeout: HTTP request timeout in seconds.
        locale: Locale pack code (e.g. ``"ar"`` for Argentina).
        mcp_server_name: Name advertised by the MCP server.
    """

    model_config = SettingsConfigDict(env_prefix="SALUDAI_", extra="ignore")

    fhir_server_url: str = "http://localhost:8080/fhir"
    fhir_auth_type: Literal["none", "bearer"] = "none"
    fhir_auth_token: str | None = None
    fhir_timeout: float = 30.0
    locale: str = "ar"
    mcp_server_name: str = "saludai"
