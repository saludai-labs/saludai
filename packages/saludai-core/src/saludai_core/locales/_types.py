"""Locale pack type definitions.

A ``LocalePack`` bundles all locale-specific configuration for a country or
region: terminology systems, FHIR profiles, extensions, custom operations,
system prompt, tool descriptions, etc.
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
        display_name: Human-readable name (e.g. ``"SNOMED CT edicion argentina"``).
        data_package: Dotted package path for ``importlib.resources``
            (e.g. ``"saludai_core.locales.ar"``).
    """

    key: str
    system_uri: str
    csv_filename: str
    display_name: str
    data_package: str


# ---------------------------------------------------------------------------
# FHIR awareness types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExtensionDef:
    """A FHIR extension defined by a local implementation guide.

    Attributes:
        url: Canonical URL of the extension.
        name: Human-readable short name.
        description: What this extension represents.
        value_type: FHIR data type of the value (e.g. ``"CodeableConcept"``).
        context: Resource path where this extension applies
            (e.g. ``"Patient"``).
    """

    url: str
    name: str
    description: str
    value_type: str
    context: str


@dataclass(frozen=True, slots=True)
class FHIRProfileDef:
    """A FHIR profile defined by a local implementation guide.

    Attributes:
        resource_type: Base FHIR resource type (e.g. ``"Patient"``).
        profile_url: Canonical URL of the StructureDefinition.
        name: Human-readable profile name.
        description: What this profile adds or constrains.
        mandatory_extensions: Extensions required by this profile.
    """

    resource_type: str
    profile_url: str
    name: str
    description: str
    mandatory_extensions: tuple[ExtensionDef, ...] = ()


@dataclass(frozen=True, slots=True)
class CustomOperationDef:
    """A custom FHIR operation defined by a local implementation.

    Attributes:
        name: Operation name including ``$`` prefix (e.g. ``"$validate"``).
        resource_type: Resource type scope, or ``None`` for server-level.
        description: What the operation does.
    """

    name: str
    resource_type: str | None
    description: str


@dataclass(frozen=True, slots=True)
class CustomSearchParamDef:
    """A custom FHIR SearchParameter defined by a local implementation.

    Attributes:
        name: Parameter name as used in search URLs.
        resource_type: Resource type this parameter applies to.
        description: What the parameter searches for.
        expression: FHIRPath expression (if known).
    """

    name: str
    resource_type: str
    description: str
    expression: str = ""


@dataclass(frozen=True, slots=True)
class IdentifierSystemDef:
    """An identifier system used in a local implementation.

    Attributes:
        system_uri: FHIR system URI for the identifier.
        name: Human-readable name (e.g. ``"DNI"``).
        description: What this identifier represents.
        resource_types: Which resources use this identifier.
    """

    system_uri: str
    name: str
    description: str
    resource_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LocaleResourceConfig:
    """Describes how a FHIR resource type is used in this locale.

    Attributes:
        resource_type: FHIR resource type (e.g. ``"Patient"``).
        usage_note: How this resource is typically used locally.
        common_search_params: Most useful search parameters for this resource.
    """

    resource_type: str
    usage_note: str
    common_search_params: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# LocalePack
# ---------------------------------------------------------------------------


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
        fhir_profiles: FHIR profiles defined by the local IG.
        extensions: FHIR extensions defined by the local IG.
        custom_operations: Custom FHIR operations available.
        custom_search_params: Custom search parameters defined locally.
        identifier_systems: Identifier systems used in this locale.
        resource_configs: Per-resource usage notes and common search params.
        validation_notes: Free-text notes about local validation rules
            (included in the agent's system prompt).
    """

    code: str
    name: str
    language: str
    terminology_systems: tuple[TerminologySystemDef, ...]
    system_prompt: str
    tool_descriptions: dict[str, str]
    tool_system_enum: tuple[str, ...]
    # FHIR awareness fields (defaults for backward compatibility)
    fhir_profiles: tuple[FHIRProfileDef, ...] = ()
    extensions: tuple[ExtensionDef, ...] = ()
    custom_operations: tuple[CustomOperationDef, ...] = ()
    custom_search_params: tuple[CustomSearchParamDef, ...] = ()
    identifier_systems: tuple[IdentifierSystemDef, ...] = ()
    resource_configs: tuple[LocaleResourceConfig, ...] = ()
    validation_notes: str = ""
