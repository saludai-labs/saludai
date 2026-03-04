"""Locale pack type definitions.

A ``LocalePack`` bundles all locale-specific configuration for a country or
region: terminology systems, system prompt, tool descriptions, etc.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TerminologySystemDef:
    """Definition of a terminology system within a locale pack.

    Attributes:
        key: Short identifier used in tool enum (e.g. ``"snomed_ct"``).
        system_uri: FHIR system URI (e.g. ``"http://snomed.info/sct"``).
        csv_filename: Name of the CSV file with concept data.
        display_name: Human-readable name (e.g. ``"SNOMED CT edición argentina"``).
        data_package: Dotted package path for ``importlib.resources``
            (e.g. ``"saludai_core.locales.ar"``).
    """

    key: str
    system_uri: str
    csv_filename: str
    display_name: str
    data_package: str


@dataclass(frozen=True, slots=True)
class LocalePack:
    """Locale-specific configuration bundle.

    Frozen and slotted for immutability and efficiency.

    Attributes:
        code: ISO-style locale code (e.g. ``"ar"``).
        name: Human-readable country/region name (e.g. ``"Argentina"``).
        language: ISO 639-1 language code (e.g. ``"es"``).
        terminology_systems: Terminology systems available in this locale.
        system_prompt: Full system prompt for the LLM agent.
        tool_descriptions: Mapping of tool name to localised description.
        tool_system_enum: Valid values for the ``system`` enum in
            ``resolve_terminology`` tool.
    """

    code: str
    name: str
    language: str
    terminology_systems: tuple[TerminologySystemDef, ...]
    system_prompt: str
    tool_descriptions: dict[str, str]
    tool_system_enum: tuple[str, ...]
