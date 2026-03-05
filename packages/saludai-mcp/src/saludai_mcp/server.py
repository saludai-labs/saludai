"""SaludAI MCP server — exposes FHIR tools via the Model Context Protocol.

Uses ``FastMCP`` from the ``mcp`` SDK to register tools that mirror the
agent's ``ToolRegistry`` (resolve_terminology, search_fhir, get_resource,
execute_code).  Designed for use with Claude Desktop, Claude Code, Cursor,
and any other MCP-compatible client.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog
from mcp.server.fastmcp import FastMCP

from saludai_agent.tools import (
    execute_code,
    execute_get_resource,
    execute_resolve_terminology,
    execute_search_fhir,
)
from saludai_core.config import FHIRConfig
from saludai_core.fhir_client import FHIRClient
from saludai_core.locales import load_locale_pack
from saludai_core.terminology import TerminologyResolver
from saludai_mcp.config import MCPConfig

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Shared state initialised in the lifespan
# ---------------------------------------------------------------------------

_fhir_client: FHIRClient | None = None
_terminology_resolver: TerminologyResolver | None = None


@asynccontextmanager
async def _lifespan(server: Any) -> AsyncIterator[None]:
    """Initialise shared resources on server startup, tear down on shutdown."""
    global _fhir_client, _terminology_resolver

    cfg = MCPConfig()
    fhir_cfg = FHIRConfig(fhir_server_url=cfg.fhir_server_url, fhir_timeout=cfg.fhir_timeout)
    _fhir_client = FHIRClient(config=fhir_cfg)

    try:
        locale_pack = load_locale_pack(cfg.locale)
    except Exception:
        locale_pack = None
        logger.warning("locale_pack_not_found", locale=cfg.locale)

    _terminology_resolver = TerminologyResolver(locale_pack=locale_pack)

    logger.info(
        "mcp_server_started",
        fhir_server=cfg.fhir_server_url,
        locale=cfg.locale,
    )

    try:
        yield
    finally:
        await _fhir_client.close()
        _fhir_client = None
        _terminology_resolver = None
        logger.info("mcp_server_stopped")


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="saludai",
    instructions=(
        "SaludAI FHIR Smart Agent — herramientas para consultar servidores FHIR R4, "
        "resolver terminologia clinica (SNOMED CT, CIE-10, LOINC), y ejecutar "
        "codigo Python para analisis de datos clinicos."
    ),
    lifespan=_lifespan,
)


# ---------------------------------------------------------------------------
# Tool: resolve_terminology
# ---------------------------------------------------------------------------


@mcp.tool()
async def resolve_terminology(
    term: str,
    system: str | None = None,
) -> str:
    """Resuelve un termino clinico a un codigo estandar (SNOMED CT, CIE-10, LOINC).

    Usa esta herramienta SIEMPRE antes de buscar con terminos medicos para
    obtener el codigo correcto.

    Args:
        term: El termino clinico a resolver (ej: 'diabetes tipo 2', 'glucosa en sangre').
        system: Sistema de terminologia opcional: "snomed_ct", "cie_10", o "loinc".
    """
    if _terminology_resolver is None:
        return '{"error": "Terminology resolver not configured"}'

    arguments: dict[str, Any] = {"term": term}
    if system is not None:
        arguments["system"] = system
    return execute_resolve_terminology(_terminology_resolver, arguments)


# ---------------------------------------------------------------------------
# Tool: search_fhir
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_fhir(
    resource_type: str,
    params: dict[str, str] | None = None,
) -> str:
    """Ejecuta una busqueda en el servidor FHIR R4.

    Devuelve un resumen del Bundle de resultados con los campos mas
    relevantes de cada recurso.

    Args:
        resource_type: Tipo de recurso FHIR (ej: 'Patient', 'Condition', 'Observation').
        params: Parametros de busqueda FHIR como pares clave-valor.
            Ejemplo: {"code": "http://snomed.info/sct|44054006", "_include": "Condition:subject"}.
            Especiales: "_summary": "count" (solo total), "_count": "200" (tamano de pagina).
    """
    if _fhir_client is None:
        return "Error: FHIR client not initialised."

    arguments: dict[str, Any] = {"resource_type": resource_type}
    if params is not None:
        arguments["params"] = params
    return await execute_search_fhir(_fhir_client, arguments)


# ---------------------------------------------------------------------------
# Tool: get_resource
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_resource(
    resource_type: str,
    resource_id: str,
) -> str:
    """Lee un recurso FHIR individual por tipo e ID.

    Usa esta herramienta para obtener detalles completos de un recurso
    especifico cuando ya tenes su referencia (ej: Patient/1005).

    Args:
        resource_type: Tipo de recurso (ej: 'Patient').
        resource_id: ID del recurso (ej: '1005').
    """
    if _fhir_client is None:
        return "Error: FHIR client not initialised."

    arguments: dict[str, Any] = {
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    return await execute_get_resource(_fhir_client, arguments)


# ---------------------------------------------------------------------------
# Tool: execute_code
# ---------------------------------------------------------------------------


@mcp.tool()
def run_python(code: str) -> str:
    """Ejecuta codigo Python para procesar y analizar datos.

    Usa esta herramienta cuando necesites contar, agrupar, filtrar o calcular
    sobre los datos obtenidos de busquedas FHIR.  Modulos disponibles: json,
    collections (Counter, defaultdict), datetime, math, statistics, re.
    Usa print() para mostrar resultados.

    Args:
        code: Codigo Python a ejecutar. Usa print() para producir output visible.
    """
    return execute_code({"code": code})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point: ``saludai-mcp``."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
