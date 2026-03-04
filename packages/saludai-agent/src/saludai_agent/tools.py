"""Agent tools: resolve_terminology, search_fhir, execute_code, and tool registry.

Tools bridge the LLM's tool-calling interface with the actual saludai-core
services (``TerminologyResolver``, ``FHIRClient``).  The ``ToolRegistry``
holds tool definitions (JSON schemas for the LLM) and execution functions.
"""

from __future__ import annotations

import io
import json
import threading
from typing import TYPE_CHECKING, Any

import structlog

from saludai_agent.exceptions import ToolExecutionError
from saludai_agent.types import ToolCall, ToolResult

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from saludai_core.fhir_client import FHIRClient
    from saludai_core.locales._types import LocalePack
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

GET_RESOURCE_DEFINITION: dict[str, Any] = {
    "name": "get_resource",
    "description": (
        "Lee un recurso FHIR individual por tipo e ID. "
        "Usá esta herramienta para obtener detalles completos de un recurso "
        "específico cuando ya tenés su referencia (ej: Patient/1005)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "resource_type": {
                "type": "string",
                "description": "Tipo de recurso (ej: 'Patient').",
            },
            "resource_id": {
                "type": "string",
                "description": "ID del recurso (ej: '1005').",
            },
        },
        "required": ["resource_type", "resource_id"],
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
                    '"_include": "Condition:subject"}. '
                    "Parámetros especiales: "
                    '"_summary": "count" devuelve solo el total sin recursos individuales; '
                    '"_count": "200" controla el tamaño de página (default: 200).'
                ),
            },
        },
        "required": ["resource_type"],
    },
}

EXECUTE_CODE_DEFINITION: dict[str, Any] = {
    "name": "execute_code",
    "description": (
        "Ejecuta código Python para procesar y analizar datos. "
        "Usá esta herramienta cuando necesites contar, agrupar, filtrar o "
        "calcular sobre los datos obtenidos de búsquedas FHIR. "
        "Módulos disponibles: json, collections (Counter, defaultdict), "
        "datetime, math, statistics, re. Usá print() para mostrar resultados."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Código Python a ejecutar. Usá print() para producir "
                    "output visible. Ejemplo: "
                    "from collections import Counter; "
                    "print(Counter(['a','b','a']).most_common())"
                ),
            },
        },
        "required": ["code"],
    },
}


# ---------------------------------------------------------------------------
# Tool execution functions
# ---------------------------------------------------------------------------

# -- execute_code sandbox ---------------------------------------------------

_CODE_TIMEOUT_SECONDS: int = 5
_CODE_MAX_OUTPUT_CHARS: int = 4000

_SAFE_BUILTINS: dict[str, Any] = {
    name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)  # type: ignore[index]
    for name in (
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "divmod",
        "enumerate",
        "filter",
        "float",
        "format",
        "frozenset",
        "hash",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "map",
        "max",
        "min",
        "next",
        "pow",
        "print",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "slice",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
    )
}
# Explicitly excluded: open, exec, eval, __import__, compile, globals, locals,
# getattr, setattr, delattr, input, breakpoint, exit, quit, memoryview, vars


_ALLOWED_MODULES: frozenset[str] = frozenset(
    ("json", "collections", "datetime", "math", "statistics", "re")
)


def execute_code(arguments: dict[str, Any]) -> str:
    """Execute sandboxed Python code and return captured stdout.

    Args:
        arguments: Tool call arguments (``code``).

    Returns:
        Captured stdout output, an error message, or a hint about missing print().
    """
    import collections
    import datetime
    import math
    import re as re_mod
    import statistics

    code = arguments.get("code", "")
    if not code.strip():
        return "Error: no code provided."

    output_buffer = io.StringIO()

    def safe_print(*args: object, **kwargs: Any) -> None:
        kwargs["file"] = output_buffer
        print(*args, **kwargs)

    allowed_modules: dict[str, Any] = {
        "json": json,
        "collections": collections,
        "datetime": datetime,
        "math": math,
        "statistics": statistics,
        "re": re_mod,
    }

    def _restricted_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name not in _ALLOWED_MODULES:
            msg = f"import of '{name}' is not allowed"
            raise ImportError(msg)
        return allowed_modules[name]

    restricted_builtins = {
        **_SAFE_BUILTINS,
        "print": safe_print,
        "__import__": _restricted_import,
    }

    restricted_globals: dict[str, Any] = {
        "__builtins__": restricted_builtins,
        **allowed_modules,
        "Counter": collections.Counter,
        "defaultdict": collections.defaultdict,
    }

    error: str | None = None

    def _run() -> None:
        nonlocal error
        try:
            compiled = compile(code, "<agent_code>", "exec")
            exec(compiled, restricted_globals)
        except Exception as exc:
            error = f"Error: {type(exc).__name__}: {exc}"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=_CODE_TIMEOUT_SECONDS)

    if thread.is_alive():
        return "Error: code execution timed out (limit: 5s)."

    if error is not None:
        return error

    output = output_buffer.getvalue()
    if not output:
        return "(No output produced. Did you forget to use print()?)"

    if len(output) > _CODE_MAX_OUTPUT_CHARS:
        return output[:_CODE_MAX_OUTPUT_CHARS] + "\n... (output truncated)"

    return output


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


_DEFAULT_COUNT = "200"


async def execute_search_fhir(
    fhir_client: FHIRClient,
    arguments: dict[str, Any],
) -> str:
    """Execute the search_fhir tool.

    Injects ``_count=200`` by default to avoid FHIR server pagination limits
    (default page size is 20).  Does not override if the caller already
    specified ``_count`` or ``_summary``.

    Args:
        fhir_client: The FHIR client instance.
        arguments: Tool call arguments (``resource_type``, optional ``params``).

    Returns:
        A token-efficient text summary of the search results.
    """
    resource_type = arguments.get("resource_type", "")
    params = arguments.get("params") or {}

    # Inject _count default when neither _count nor _summary is set
    if "_count" not in params and "_summary" not in params:
        params = {**params, "_count": _DEFAULT_COUNT}

    bundle = await fhir_client.search(resource_type, params)
    return format_bundle_summary(bundle)


async def execute_get_resource(
    fhir_client: FHIRClient,
    arguments: dict[str, Any],
) -> str:
    """Execute the get_resource tool.

    Args:
        fhir_client: The FHIR client instance.
        arguments: Tool call arguments (``resource_type``, ``resource_id``).

    Returns:
        A token-efficient text summary of the resource.
    """
    resource_type = arguments.get("resource_type", "")
    resource_id = arguments.get("resource_id", "")
    resource = await fhir_client.read_raw(resource_type, resource_id)
    return _summarize_resource(resource_type, resource)


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


def format_bundle_summary(bundle: dict[str, Any] | Any) -> str:
    """Format a FHIR Bundle into a token-efficient text summary.

    Extracts key fields per resource type so the LLM can reason about the
    results without processing raw JSON.

    Args:
        bundle: A FHIR Bundle as a raw dict (from ``FHIRClient.search``)
            or a ``fhir.resources`` Bundle instance.

    Returns:
        A human-readable summary string.
    """
    entries = _get(bundle, "entry") or []
    total = _get(bundle, "total")

    if not entries:
        # _summary=count returns {total: N} with no entry array
        if total is not None and total > 0:
            return f"Total count: {total} (summary-only, no individual entries returned)."
        return "No results found."

    # Group resources by type
    by_type: dict[str, list[Any]] = {}
    for entry in entries:
        resource = _get(entry, "resource")
        if resource is None:
            continue
        rtype = _get(resource, "resourceType") or "Unknown"
        by_type.setdefault(rtype, []).append(resource)

    # Build counts line
    total_server = _get(bundle, "total")
    total_page = sum(len(v) for v in by_type.values())
    type_counts = ", ".join(f"{len(v)} {k}" for k, v in by_type.items())
    if total_server is not None:
        lines: list[str] = [
            f"Found {total_page} resources on this page "
            f"(server total: {total_server}). Types: {type_counts}."
        ]
    else:
        lines = [f"Found {total_page} resources ({type_counts})."]
    lines.append("")

    # Summarize each type
    for rtype, resources in by_type.items():
        lines.append(f"## {rtype} ({len(resources)})")
        for resource in resources:
            summary = _summarize_resource(rtype, resource)
            lines.append(f"- {summary}")
        lines.append("")

    return "\n".join(lines)


def _get(obj: Any, key: str) -> Any:
    """Get a field from a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _summarize_resource(resource_type: str, resource: Any) -> str:
    """Summarize a single FHIR resource into a compact string."""
    parts: list[str] = []

    # ID
    rid = _get(resource, "id")
    if rid:
        parts.append(f"{resource_type}/{rid}")

    # Codeable concept fields
    for field_name in ("code", "medicationCodeableConcept", "vaccineCode"):
        codeable = _get(resource, field_name)
        if codeable:
            text = _extract_codeable_concept(codeable)
            if text:
                parts.append(text)
            break

    # Name (Patient)
    names = _get(resource, "name")
    if names and len(names) > 0:
        name = names[0]
        family = _get(name, "family") or ""
        given = _get(name, "given") or []
        full_name = f"{' '.join(given)} {family}".strip()
        if full_name:
            parts.append(f"name={full_name}")

    # Class (Encounter)
    enc_class = _get(resource, "class")
    if enc_class:
        class_display = _get(enc_class, "display") or _get(enc_class, "code") or ""
        if class_display:
            parts.append(f"class={class_display}")

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
        value = _get(resource, field_name)
        if value is not None:
            parts.append(f"{field_name}={value}")

    # Subject reference
    subject = _get(resource, "subject") or _get(resource, "patient")
    if subject:
        ref = _get(subject, "reference")
        if ref:
            parts.append(f"subject={ref}")

    # Value quantity (Observation)
    vq = _get(resource, "valueQuantity")
    if vq:
        val = _get(vq, "value")
        unit = _get(vq, "unit") or _get(vq, "code") or ""
        if val is not None:
            parts.append(f"value={val} {unit}".strip())

    # Clinical status
    clinical_status = _get(resource, "clinicalStatus")
    if clinical_status:
        text = _extract_codeable_concept(clinical_status)
        if text:
            parts.append(f"clinicalStatus={text}")

    # Period (Encounter)
    period = _get(resource, "period")
    if period:
        start = _get(period, "start") or ""
        end = _get(period, "end") or ""
        if start:
            parts.append(f"period={start}..{end}")

    # Address (Patient)
    addresses = _get(resource, "address")
    if addresses and len(addresses) > 0:
        addr = addresses[0]
        city = _get(addr, "city") or ""
        state = _get(addr, "state") or ""
        addr_text = ", ".join(p for p in [city, state] if p)
        if addr_text:
            parts.append(f"address={addr_text}")

    return " | ".join(parts) if parts else "(empty resource)"


def _extract_codeable_concept(codeable: Any) -> str:
    """Extract a display string from a CodeableConcept (dict or object)."""
    text = _get(codeable, "text")
    if text:
        return text

    coding_list = _get(codeable, "coding")
    if coding_list and len(coding_list) > 0:
        coding = coding_list[0]
        display = _get(coding, "display")
        code = _get(coding, "code")
        system = _get(coding, "system")
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
        locale_pack: Locale pack for localised tool descriptions and enum values.
    """

    def __init__(
        self,
        fhir_client: FHIRClient,
        terminology_resolver: TerminologyResolver | None = None,
        locale_pack: LocalePack | None = None,
    ) -> None:
        self._fhir_client = fhir_client
        self._terminology_resolver = terminology_resolver
        self._locale_pack = locale_pack
        self._tools: dict[str, dict[str, Any]] = {}
        self._executors: dict[str, Callable[..., Awaitable[str] | str]] = {}

        # Build tool definitions — use locale pack overrides when available
        search_def = self._apply_locale("search_fhir", SEARCH_FHIR_DEFINITION)
        get_def = self._apply_locale("get_resource", GET_RESOURCE_DEFINITION)
        code_def = self._apply_locale("execute_code", EXECUTE_CODE_DEFINITION)

        # Register search_fhir (always available)
        self._tools["search_fhir"] = search_def
        self._executors["search_fhir"] = self._execute_search_fhir

        # Register get_resource (always available)
        self._tools["get_resource"] = get_def
        self._executors["get_resource"] = self._execute_get_resource

        # Register execute_code (always available, no external deps)
        self._tools["execute_code"] = code_def
        self._executors["execute_code"] = self._execute_code

        # Register resolve_terminology (only if resolver is provided)
        if terminology_resolver is not None:
            term_def = self._build_resolve_terminology_def()
            self._tools["resolve_terminology"] = term_def
            self._executors["resolve_terminology"] = self._execute_resolve_terminology

    def _apply_locale(self, tool_name: str, definition: dict[str, Any]) -> dict[str, Any]:
        """Apply locale pack description override to a tool definition."""
        if self._locale_pack is None:
            return definition
        desc = self._locale_pack.tool_descriptions.get(tool_name)
        if desc is None:
            return definition
        return {**definition, "description": desc}

    def _build_resolve_terminology_def(self) -> dict[str, Any]:
        """Build resolve_terminology definition, using locale pack enum if available."""
        base = dict(RESOLVE_TERMINOLOGY_DEFINITION)
        if self._locale_pack is not None:
            desc = self._locale_pack.tool_descriptions.get("resolve_terminology")
            if desc is not None:
                base = {**base, "description": desc}
            # Override system enum from locale pack
            if self._locale_pack.tool_system_enum:
                base = {
                    **base,
                    "input_schema": {
                        **base["input_schema"],
                        "properties": {
                            **base["input_schema"]["properties"],
                            "system": {
                                **base["input_schema"]["properties"]["system"],
                                "enum": list(self._locale_pack.tool_system_enum),
                            },
                        },
                    },
                }
        return base

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

    async def _execute_get_resource(self, arguments: dict[str, Any]) -> str:
        """Async wrapper for get_resource."""
        return await execute_get_resource(self._fhir_client, arguments)

    def _execute_code(self, arguments: dict[str, Any]) -> str:
        """Sync wrapper for execute_code."""
        return execute_code(arguments)
