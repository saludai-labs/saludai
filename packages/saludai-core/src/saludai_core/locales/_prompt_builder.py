"""Dynamic prompt section builder from locale pack FHIR metadata.

Generates a markdown section describing the local FHIR implementation
(profiles, extensions, identifiers, operations, resource usage) that gets
appended to the agent's system prompt so the LLM is *aware* of the local
context without hardcoding it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saludai_core.locales._types import LocalePack


def build_fhir_awareness_section(pack: LocalePack) -> str:
    """Build a FHIR awareness section from locale pack metadata.

    Returns an empty string if the pack has no FHIR awareness data.

    Args:
        pack: The locale pack to generate the section from.

    Returns:
        A markdown-formatted string to append to the system prompt.
    """
    parts: list[str] = []

    if pack.fhir_profiles:
        lines = [f"## Perfiles FHIR locales ({pack.name})\n"]
        for p in pack.fhir_profiles:
            lines.append(f"- **{p.resource_type}**: {p.name} — {p.description}")
            if p.mandatory_extensions:
                ext_names = ", ".join(e.name for e in p.mandatory_extensions)
                lines.append(f"  - Extensiones obligatorias: {ext_names}")
        parts.append("\n".join(lines))

    if pack.extensions:
        lines = [f"## Extensiones FHIR ({pack.name})\n"]
        for e in pack.extensions:
            lines.append(
                f"- **{e.name}** (`{e.url}`): {e.description} [{e.value_type}, en {e.context}]"
            )
        parts.append("\n".join(lines))

    if pack.identifier_systems:
        lines = [f"## Sistemas de identificacion ({pack.name})\n"]
        for i in pack.identifier_systems:
            resources = ", ".join(i.resource_types) if i.resource_types else "varios"
            lines.append(f"- **{i.name}** (`{i.system_uri}`): {i.description} [{resources}]")
        parts.append("\n".join(lines))

    if pack.custom_operations:
        lines = ["## Operaciones FHIR custom\n"]
        for op in pack.custom_operations:
            scope = op.resource_type or "server"
            lines.append(f"- **{op.name}** ({scope}): {op.description}")
        parts.append("\n".join(lines))

    if pack.custom_search_params:
        lines = ["## Parametros de busqueda custom\n"]
        for sp in pack.custom_search_params:
            lines.append(f"- **{sp.name}** ({sp.resource_type}): {sp.description}")
        parts.append("\n".join(lines))

    if pack.resource_configs:
        lines = [f"## Recursos FHIR en {pack.name}\n"]
        for rc in pack.resource_configs:
            params = ", ".join(rc.common_search_params) if rc.common_search_params else ""
            lines.append(f"- **{rc.resource_type}**: {rc.usage_note}")
            if params:
                lines.append(f"  - Parametros de busqueda comunes: {params}")
        parts.append("\n".join(lines))

    if pack.validation_notes:
        parts.append(f"## Reglas de validacion locales\n\n{pack.validation_notes}")

    if not parts:
        return ""

    return "\n\n" + "\n\n".join(parts) + "\n"
