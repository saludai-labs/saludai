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
    from collections.abc import Awaitable, Callable, Sequence

    from saludai_core.fhir_client import FHIRClient
    from saludai_core.locales._types import ExtensionDef, LocalePack
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
                "enum": ["snomed_ct", "cie_10", "loinc", "atc"],
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

COUNT_FHIR_DEFINITION: dict[str, Any] = {
    "name": "count_fhir",
    "description": (
        "Cuenta recursos FHIR en el servidor sin transferir datos. "
        "Usa _summary=count internamente. Soporta _has para conteos "
        "cross-resource. "
        "Ejemplo: count_fhir('Patient', {'_has:Condition:subject:code': "
        "'http://snomed.info/sct|44054006'}) cuenta pacientes con diabetes tipo 2."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "resource_type": {
                "type": "string",
                "description": "Tipo de recurso FHIR a contar (ej: 'Patient').",
            },
            "params": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": (
                    "Parametros de busqueda FHIR como pares clave-valor. "
                    "No incluir _summary (se agrega automaticamente). "
                    "Ejemplo: {'_has:Condition:subject:code': 'http://snomed.info/sct|44054006', "
                    "'address-state': 'Buenos Aires'}"
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
        "La variable `entries` contiene los recursos FHIR de la última búsqueda "
        "(lista de dicts). "
        "La variable `store` es un dict persistente: guardá resultados intermedios "
        "con `store['clave'] = valor` para no perderlos entre búsquedas. "
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


def execute_code(
    arguments: dict[str, Any],
    extra_globals: dict[str, Any] | None = None,
) -> str:
    """Execute sandboxed Python code and return captured stdout.

    Args:
        arguments: Tool call arguments (``code``).
        extra_globals: Additional variables to inject into the sandbox
            (e.g. ``{"entries": [...]}`` from the FHIR search scratchpad).

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
        **(extra_globals or {}),
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
    "atc": "ATC",
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
    extension_defs: Sequence[ExtensionDef] = (),
) -> str:
    """Execute the search_fhir tool.

    Injects ``_count=200`` by default to avoid FHIR server pagination limits
    (default page size is 20).  Uses ``search_all()`` to automatically follow
    pagination ``next`` links, unless ``_summary`` is set (count-only queries
    don't need pagination).

    Args:
        fhir_client: The FHIR client instance.
        arguments: Tool call arguments (``resource_type``, optional ``params``).
        extension_defs: Extension definitions for human-readable extension output.

    Returns:
        A token-efficient text summary of the search results.
    """
    resource_type = arguments.get("resource_type", "")
    params = arguments.get("params") or {}

    # _summary queries don't need pagination — single page with count only
    if "_summary" in params:
        bundle = await fhir_client.search(resource_type, params)
        return format_bundle_summary(bundle, extension_defs=extension_defs)

    # Inject _count default when not specified
    if "_count" not in params:
        params = {**params, "_count": _DEFAULT_COUNT}

    # Use search_all to follow pagination next links automatically
    bundle = await fhir_client.search_all(resource_type, params)
    return format_bundle_summary(bundle, extension_defs=extension_defs)


async def execute_count_fhir(
    fhir_client: FHIRClient,
    arguments: dict[str, Any],
) -> str:
    """Execute the count_fhir tool.

    Always adds ``_summary=count`` to the search params.  Returns only
    the numeric total as a string.

    Args:
        fhir_client: The FHIR client instance.
        arguments: Tool call arguments (``resource_type``, optional ``params``).

    Returns:
        A string with the count result (e.g. ``"Total: 42"``).
    """
    resource_type = arguments.get("resource_type", "")
    params = arguments.get("params") or {}
    # Always force _summary=count
    params = {**params, "_summary": "count"}
    bundle = await fhir_client.search(resource_type, params)
    total = bundle.get("total") if isinstance(bundle, dict) else getattr(bundle, "total", None)
    if total is not None:
        return f"Total: {total}"
    return "Total: 0 (no total returned by server)"


async def execute_get_resource(
    fhir_client: FHIRClient,
    arguments: dict[str, Any],
    extension_defs: Sequence[ExtensionDef] = (),
) -> str:
    """Execute the get_resource tool.

    Args:
        fhir_client: The FHIR client instance.
        arguments: Tool call arguments (``resource_type``, ``resource_id``).
        extension_defs: Extension definitions for human-readable extension output.

    Returns:
        A token-efficient text summary of the resource.
    """
    resource_type = arguments.get("resource_type", "")
    resource_id = arguments.get("resource_id", "")
    resource = await fhir_client.read_raw(resource_type, resource_id)
    return _summarize_resource(resource_type, resource, extension_defs=extension_defs)


# ---------------------------------------------------------------------------
# Extension extraction
# ---------------------------------------------------------------------------

# Map ExtensionDef.value_type → FHIR value[x] field name
_VALUE_TYPE_FIELD: dict[str, str] = {
    "string": "valueString",
    "boolean": "valueBoolean",
    "code": "valueCode",
    "CodeableConcept": "valueCodeableConcept",
    "Coding": "valueCoding",
    "Address": "valueAddress",
}


def _extract_extension_value(ext_data: dict[str, Any], value_type: str) -> str | None:
    """Extract a display value from a FHIR extension entry based on its value type."""
    field = _VALUE_TYPE_FIELD.get(value_type)
    if field is None:
        return None
    raw = ext_data.get(field)
    if raw is None:
        return None

    if value_type in ("string", "code"):
        return str(raw)
    if value_type == "boolean":
        return str(raw)
    if value_type == "CodeableConcept":
        return _extract_codeable_concept(raw) or None
    if value_type == "Coding":
        display = _get(raw, "display")
        if display:
            return str(display)
        code = _get(raw, "code")
        return str(code) if code else None
    if value_type == "Address":
        parts = [
            _get(raw, "city"),
            _get(raw, "state"),
            _get(raw, "country"),
        ]
        text = ", ".join(str(p) for p in parts if p)
        return text or None
    return None


def _extract_extensions(
    resource: dict[str, Any],
    extension_defs: Sequence[ExtensionDef],
) -> list[str]:
    """Extract human-readable name=value pairs from top-level extensions.

    Uses locale pack ``ExtensionDef`` entries to translate opaque extension
    URLs into readable labels.  Unknown extension URLs are skipped.

    Args:
        resource: A FHIR resource as a raw dict.
        extension_defs: Extension definitions from the locale pack.

    Returns:
        A list of ``"name=value"`` strings for recognised extensions.
    """
    extensions = resource.get("extension")
    if not extensions or not extension_defs:
        return []

    # Build a lookup by URL for O(1) matching
    url_map: dict[str, ExtensionDef] = {ed.url: ed for ed in extension_defs}

    pairs: list[str] = []
    for ext in extensions:
        url = ext.get("url", "")
        edef = url_map.get(url)
        if edef is None:
            continue
        value = _extract_extension_value(ext, edef.value_type)
        if value is not None:
            pairs.append(f"{edef.name}={value}")

    return pairs


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


_SMART_SUMMARY_THRESHOLD: int = 30


def format_bundle_summary(
    bundle: dict[str, Any] | Any,
    extension_defs: Sequence[ExtensionDef] = (),
) -> str:
    """Format a FHIR Bundle into a token-efficient text summary.

    For small result sets (≤30 resources), lists every resource individually.
    For large result sets (>30), produces FHIR-aware aggregate statistics
    (unique patients, code distributions, date ranges, status breakdown) plus
    a sample of 10 resources.  The full data is accessible in ``execute_code``
    via the ``entries`` variable.

    Args:
        bundle: A FHIR Bundle as a raw dict (from ``FHIRClient.search``)
            or a ``fhir.resources`` Bundle instance.
        extension_defs: Extension definitions from the locale pack for
            translating extension URLs into human-readable labels.

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

    total_resources = sum(len(v) for v in by_type.values())
    total_server = _get(bundle, "total")
    type_counts = ", ".join(f"{len(v)} {k}" for k, v in by_type.items())

    # Header
    if total_server is not None:
        lines: list[str] = [
            f"Found {total_resources} resources "
            f"(server total: {total_server}). Types: {type_counts}."
        ]
    else:
        lines = [f"Found {total_resources} resources ({type_counts})."]
    lines.append("")

    # Small result set — list everything
    if total_resources <= _SMART_SUMMARY_THRESHOLD:
        for rtype, resources in by_type.items():
            lines.append(f"## {rtype} ({len(resources)})")
            for resource in resources:
                summary = _summarize_resource(rtype, resource, extension_defs=extension_defs)
                lines.append(f"- {summary}")
            lines.append("")
        return "\n".join(lines)

    # Large result set — smart summary per type + sample
    for rtype, resources in by_type.items():
        lines.append(f"## {rtype} ({len(resources)})")
        lines.append(_compute_fhir_stats(resources))
        lines.append("")
        # Sample of first 10
        sample_size = min(10, len(resources))
        lines.append(f"Sample ({sample_size} of {len(resources)}):")
        for resource in resources[:sample_size]:
            summary = _summarize_resource(rtype, resource, extension_defs=extension_defs)
            lines.append(f"- {summary}")
        lines.append("")

    lines.append(f"Full data available as `entries` in execute_code ({total_resources} records).")
    return "\n".join(lines)


def _compute_fhir_stats(resources: list[Any]) -> str:
    """Compute FHIR-aware aggregate statistics for a list of resources.

    Pre-computes the metrics most useful for clinical data questions:
    unique patients, code distributions, date ranges, and status breakdown.
    """
    from collections import Counter

    stats: list[str] = []

    # Unique patients (by subject/patient reference)
    subjects: set[str] = set()
    for r in resources:
        ref = _get(_get(r, "subject") or _get(r, "patient") or {}, "reference")
        if ref:
            subjects.add(ref)
    if subjects:
        stats.append(f"Unique patients: {len(subjects)}")

    # Code distribution (top 8)
    codes: list[str] = []
    for r in resources:
        for field in ("code", "medicationCodeableConcept", "vaccineCode"):
            codeable = _get(r, field)
            if codeable:
                text = _extract_codeable_concept(codeable)
                if text:
                    codes.append(text)
                break
    if codes:
        top = Counter(codes).most_common(8)
        dist = ", ".join(f"{name} ({count})" for name, count in top)
        if len(Counter(codes)) > 8:
            dist += f", ... ({len(Counter(codes))} distinct)"
        stats.append(f"Code distribution: {dist}")

    # Date range
    dates: list[str] = []
    for r in resources:
        date_fields = (
            "effectiveDateTime", "onsetDateTime", "authoredOn",
            "performedDateTime", "occurrenceDateTime",
        )
        for field in date_fields:
            val = _get(r, field)
            if val:
                dates.append(str(val)[:10])
                break
        period = _get(r, "period")
        if period:
            start = _get(period, "start")
            if start:
                dates.append(str(start)[:10])
    if dates:
        stats.append(f"Date range: {min(dates)} .. {max(dates)}")

    # Status breakdown
    statuses: list[str] = []
    for r in resources:
        status = _get(r, "status")
        if status:
            statuses.append(str(status))
        else:
            cs = _get(r, "clinicalStatus")
            if cs:
                text = _extract_codeable_concept(cs)
                if text:
                    statuses.append(text)
    if statuses:
        status_dist = Counter(statuses).most_common(5)
        stats.append(f"Status: {', '.join(f'{s} ({c})' for s, c in status_dist)}")

    return "\n".join(f"  {s}" for s in stats) if stats else "  (no stats available)"


def _get(obj: Any, key: str) -> Any:
    """Get a field from a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _summarize_resource(
    resource_type: str,
    resource: Any,
    extension_defs: Sequence[ExtensionDef] = (),
) -> str:
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

    # Extensions (from locale pack)
    if extension_defs and isinstance(resource, dict):
        ext_pairs = _extract_extensions(resource, extension_defs)
        parts.extend(ext_pairs)

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
        self._extension_defs = locale_pack.extensions if locale_pack else ()
        # Scratchpad: raw FHIR entries from the last search, accessible in execute_code
        self._last_search_entries: list[dict[str, Any]] = []
        # Persistent store: survives across searches so the agent can save
        # intermediate results (e.g., patient sets) without re-querying.
        self._store: dict[str, Any] = {}
        self._tools: dict[str, dict[str, Any]] = {}
        self._executors: dict[str, Callable[..., Awaitable[str] | str]] = {}

        # Build tool definitions — use locale pack overrides when available
        search_def = self._apply_locale("search_fhir", SEARCH_FHIR_DEFINITION)
        get_def = self._apply_locale("get_resource", GET_RESOURCE_DEFINITION)
        code_def = self._apply_locale("execute_code", EXECUTE_CODE_DEFINITION)
        count_def = self._apply_locale("count_fhir", COUNT_FHIR_DEFINITION)

        # Register search_fhir (always available)
        self._tools["search_fhir"] = search_def
        self._executors["search_fhir"] = self._execute_search_fhir

        # Register count_fhir (always available)
        self._tools["count_fhir"] = count_def
        self._executors["count_fhir"] = self._execute_count_fhir

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
        """Async wrapper for search_fhir.  Stores raw entries in scratchpad."""
        resource_type = arguments.get("resource_type", "")
        params = arguments.get("params") or {}

        # _summary queries: no pagination, no scratchpad
        if "_summary" in params:
            bundle = await self._fhir_client.search(resource_type, params)
            self._last_search_entries = []
            return format_bundle_summary(bundle, extension_defs=self._extension_defs)

        # Inject default _count
        if "_count" not in params:
            params = {**params, "_count": _DEFAULT_COUNT}

        # Fetch all pages
        bundle = await self._fhir_client.search_all(resource_type, params)

        # Store raw entries in scratchpad for execute_code
        self._last_search_entries = [
            entry.get("resource", entry)
            for entry in (bundle.get("entry") or [])
            if isinstance(entry, dict)
        ]

        return format_bundle_summary(bundle, extension_defs=self._extension_defs)

    async def _execute_count_fhir(self, arguments: dict[str, Any]) -> str:
        """Async wrapper for count_fhir.  Does not update scratchpad."""
        return await execute_count_fhir(self._fhir_client, arguments)

    async def _execute_get_resource(self, arguments: dict[str, Any]) -> str:
        """Async wrapper for get_resource."""
        return await execute_get_resource(
            self._fhir_client, arguments, extension_defs=self._extension_defs
        )

    def _execute_code(self, arguments: dict[str, Any]) -> str:
        """Sync wrapper for execute_code.  Injects ``entries`` + ``store``."""
        return execute_code(
            arguments,
            extra_globals={
                "entries": self._last_search_entries,
                "store": self._store,
            },
        )
