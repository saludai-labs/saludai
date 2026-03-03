"""Agent tools: resolve_terminology, search_fhir, and tool registry.

Tools bridge the LLM's tool-calling interface with the actual saludai-core
services (``TerminologyResolver``, ``FHIRClient``).  The ``ToolRegistry``
holds tool definitions (JSON schemas for the LLM) and execution functions.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from saludai_agent.exceptions import ToolExecutionError
from saludai_agent.types import ToolCall, ToolResult

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from saludai_core.fhir_client import FHIRClient
    from saludai_core.terminology import TerminologyResolver, TerminologySystem

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic tool format — converted to OpenAI in llm.py)
# ---------------------------------------------------------------------------

RESOLVE_TERMINOLOGY_DEFINITION: dict[str, Any] = {
    "name": "resolve_terminology",
    "description": (
        "Resuelve un término clínico en lenguaje natural a un código estándar "
        "(SNOMED CT, CIE-10, o LOINC). Usá esta herramienta SIEMPRE antes de "
        "buscar con términos médicos para obtener el código correcto."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "term": {
                "type": "string",
                "description": (
                    "El término clínico a resolver (ej: 'diabetes tipo 2', 'glucosa en sangre')."
                ),
            },
            "system": {
                "type": "string",
                "enum": ["snomed_ct", "cie_10", "loinc"],
                "description": (
                    "Sistema de terminología opcional para restringir la búsqueda. "
                    "Si no se especifica, busca en todos los sistemas."
                ),
            },
        },
        "required": ["term"],
    },
}

SEARCH_FHIR_DEFINITION: dict[str, Any] = {
    "name": "search_fhir",
    "description": (
        "Ejecuta una búsqueda en el servidor FHIR R4. Devuelve un resumen "
        "del Bundle de resultados con los campos más relevantes de cada recurso."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "resource_type": {
                "type": "string",
                "description": (
                    "Tipo de recurso FHIR a buscar (ej: 'Patient', 'Condition', "
                    "'Observation', 'MedicationRequest')."
                ),
            },
            "params": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": (
                    "Parámetros de búsqueda FHIR como pares clave-valor. "
                    'Ejemplo: {"code": "http://snomed.info/sct|44054006", '
                    '"_include": "Condition:subject"}'
                ),
            },
        },
        "required": ["resource_type"],
    },
}


# ---------------------------------------------------------------------------
# Tool execution functions
# ---------------------------------------------------------------------------

_SYSTEM_MAP: dict[str, str] = {
    "snomed_ct": "SNOMED_CT",
    "cie_10": "CIE_10",
    "loinc": "LOINC",
}


def _resolve_system(system_str: str | None) -> TerminologySystem | None:
    """Convert a tool-level system string to a ``TerminologySystem`` enum."""
    if not system_str:
        return None
    from saludai_core.terminology import TerminologySystem

    mapped = _SYSTEM_MAP.get(system_str)
    if mapped is None:
        return None
    return TerminologySystem[mapped]


def execute_resolve_terminology(
    resolver: TerminologyResolver,
    arguments: dict[str, Any],
) -> str:
    """Execute the resolve_terminology tool.

    Args:
        resolver: The terminology resolver instance.
        arguments: Tool call arguments (``term``, optional ``system``).

    Returns:
        JSON string with the resolution result.
    """
    term = arguments.get("term", "")
    system_str = arguments.get("system")
    system = _resolve_system(system_str)

    match = resolver.resolve(term, system=system)

    result: dict[str, Any] = {
        "query": match.query,
        "match_type": match.match_type.value,
        "score": match.score,
        "is_confident": match.is_confident,
    }

    if match.concept:
        result["code"] = match.concept.code
        result["system"] = match.concept.system.value
        result["display"] = match.concept.display
    else:
        result["code"] = None
        result["system"] = None
        result["display"] = None

    return json.dumps(result, ensure_ascii=False)


async def execute_search_fhir(
    fhir_client: FHIRClient,
    arguments: dict[str, Any],
) -> str:
    """Execute the search_fhir tool.

    Args:
        fhir_client: The FHIR client instance.
        arguments: Tool call arguments (``resource_type``, optional ``params``).

    Returns:
        A token-efficient text summary of the search results.
    """
    resource_type = arguments.get("resource_type", "")
    params = arguments.get("params")

    bundle = await fhir_client.search(resource_type, params)
    return format_bundle_summary(bundle)


# ---------------------------------------------------------------------------
# Bundle summary formatter
# ---------------------------------------------------------------------------

# Fields to extract per resource type for concise summaries
_RESOURCE_EXTRACTORS: dict[str, list[str]] = {
    "Patient": ["id", "name", "gender", "birthDate", "address"],
    "Condition": ["id", "code", "subject", "onsetDateTime", "clinicalStatus"],
    "Observation": ["id", "code", "subject", "valueQuantity", "effectiveDateTime", "status"],
    "MedicationRequest": ["id", "medicationCodeableConcept", "subject", "status", "authoredOn"],
    "MedicationStatement": ["id", "medicationCodeableConcept", "subject", "status"],
    "Encounter": ["id", "class", "subject", "status", "period"],
    "Procedure": ["id", "code", "subject", "status", "performedDateTime"],
    "DiagnosticReport": ["id", "code", "subject", "status", "effectiveDateTime"],
    "AllergyIntolerance": ["id", "code", "patient", "clinicalStatus"],
    "Immunization": ["id", "vaccineCode", "patient", "occurrenceDateTime", "status"],
}


def format_bundle_summary(bundle: Any) -> str:
    """Format a FHIR Bundle into a token-efficient text summary.

    Extracts key fields per resource type so the LLM can reason about the
    results without processing raw JSON.

    Args:
        bundle: A ``fhir.resources.bundle.Bundle`` instance.

    Returns:
        A human-readable summary string.
    """
    entries = bundle.entry or []
    if not entries:
        total = bundle.total if bundle.total is not None else 0
        return f"No results found (total: {total})."

    # Group resources by type
    by_type: dict[str, list[Any]] = {}
    for entry in entries:
        resource = entry.resource
        if resource is None:
            continue
        rtype = resource.get_resource_type()
        by_type.setdefault(rtype, []).append(resource)

    # Build counts line
    total_count = sum(len(v) for v in by_type.values())
    type_counts = ", ".join(f"{len(v)} {k}" for k, v in by_type.items())
    lines: list[str] = [f"Found {total_count} resources ({type_counts})."]
    lines.append("")

    # Summarize each type
    for rtype, resources in by_type.items():
        lines.append(f"## {rtype} ({len(resources)})")
        for resource in resources:
            summary = _summarize_resource(rtype, resource)
            lines.append(f"- {summary}")
        lines.append("")

    return "\n".join(lines)


def _summarize_resource(resource_type: str, resource: Any) -> str:
    """Summarize a single FHIR resource into a compact string."""
    parts: list[str] = []

    # ID
    rid = getattr(resource, "id", None)
    if rid:
        parts.append(f"{resource_type}/{rid}")

    # Codeable concept fields
    for field_name in ("code", "medicationCodeableConcept", "vaccineCode"):
        codeable = getattr(resource, field_name, None)
        if codeable:
            text = _extract_codeable_concept(codeable)
            if text:
                parts.append(text)
            break

    # Name (Patient)
    names = getattr(resource, "name", None)
    if names and len(names) > 0:
        name = names[0]
        family = getattr(name, "family", "") or ""
        given = getattr(name, "given", None) or []
        full_name = f"{' '.join(given)} {family}".strip()
        if full_name:
            parts.append(f"name={full_name}")

    # Simple fields
    for field_name in (
        "gender",
        "birthDate",
        "status",
        "onsetDateTime",
        "effectiveDateTime",
        "authoredOn",
        "performedDateTime",
        "occurrenceDateTime",
    ):
        value = getattr(resource, field_name, None)
        if value is not None:
            parts.append(f"{field_name}={value}")

    # Subject reference
    subject = getattr(resource, "subject", None) or getattr(resource, "patient", None)
    if subject:
        ref = getattr(subject, "reference", None)
        if ref:
            parts.append(f"subject={ref}")

    # Value quantity (Observation)
    vq = getattr(resource, "valueQuantity", None)
    if vq:
        val = getattr(vq, "value", None)
        unit = getattr(vq, "unit", None) or getattr(vq, "code", "")
        if val is not None:
            parts.append(f"value={val} {unit}".strip())

    # Clinical status
    clinical_status = getattr(resource, "clinicalStatus", None)
    if clinical_status:
        text = _extract_codeable_concept(clinical_status)
        if text:
            parts.append(f"clinicalStatus={text}")

    # Address (Patient)
    addresses = getattr(resource, "address", None)
    if addresses and len(addresses) > 0:
        addr = addresses[0]
        city = getattr(addr, "city", "") or ""
        state = getattr(addr, "state", "") or ""
        addr_text = ", ".join(p for p in [city, state] if p)
        if addr_text:
            parts.append(f"address={addr_text}")

    return " | ".join(parts) if parts else "(empty resource)"


def _extract_codeable_concept(codeable: Any) -> str:
    """Extract a display string from a CodeableConcept."""
    text = getattr(codeable, "text", None)
    if text:
        return text

    coding_list = getattr(codeable, "coding", None)
    if coding_list and len(coding_list) > 0:
        coding = coding_list[0]
        display = getattr(coding, "display", None)
        code = getattr(coding, "code", None)
        system = getattr(coding, "system", None)
        if display:
            return f"{display} ({code})" if code else display
        if code:
            return f"{system}|{code}" if system else code
    return ""


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Registry of tools available to the agent.

    Holds tool definitions (JSON schemas for the LLM) and execution functions.

    Args:
        fhir_client: FHIR client for search_fhir tool.
        terminology_resolver: Terminology resolver for resolve_terminology tool.
    """

    def __init__(
        self,
        fhir_client: FHIRClient,
        terminology_resolver: TerminologyResolver | None = None,
    ) -> None:
        self._fhir_client = fhir_client
        self._terminology_resolver = terminology_resolver
        self._tools: dict[str, dict[str, Any]] = {}
        self._executors: dict[str, Callable[..., Awaitable[str] | str]] = {}

        # Register search_fhir (always available)
        self._tools["search_fhir"] = SEARCH_FHIR_DEFINITION
        self._executors["search_fhir"] = self._execute_search_fhir

        # Register resolve_terminology (only if resolver is provided)
        if terminology_resolver is not None:
            self._tools["resolve_terminology"] = RESOLVE_TERMINOLOGY_DEFINITION
            self._executors["resolve_terminology"] = self._execute_resolve_terminology

    def definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions for the LLM."""
        return list(self._tools.values())

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call and return the result.

        Args:
            tool_call: The tool call to execute.

        Returns:
            A ``ToolResult`` with the execution output.
        """
        executor = self._executors.get(tool_call.name)
        if executor is None:
            logger.warning("unknown_tool_called", tool_name=tool_call.name)
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Error: unknown tool '{tool_call.name}'",
                is_error=True,
            )

        try:
            logger.info("tool_executing", tool_name=tool_call.name, arguments=tool_call.arguments)
            result = executor(tool_call.arguments)
            # Handle both sync and async executors
            if hasattr(result, "__await__"):
                content = await result
            else:
                content = result
            logger.info("tool_executed", tool_name=tool_call.name, result_length=len(content))
            return ToolResult(tool_call_id=tool_call.id, content=content)
        except Exception as exc:
            logger.error("tool_execution_failed", tool_name=tool_call.name, error=str(exc))
            raise ToolExecutionError(
                f"Tool '{tool_call.name}' failed: {exc}",
                tool_name=tool_call.name,
                cause=exc,
            ) from exc

    def _execute_resolve_terminology(self, arguments: dict[str, Any]) -> str:
        """Sync wrapper for resolve_terminology."""
        if self._terminology_resolver is None:
            return json.dumps({"error": "Terminology resolver not configured"})
        return execute_resolve_terminology(self._terminology_resolver, arguments)

    async def _execute_search_fhir(self, arguments: dict[str, Any]) -> str:
        """Async wrapper for search_fhir."""
        return await execute_search_fhir(self._fhir_client, arguments)
