"""English (US) locale pack definition.

Bundles all locale-specific configuration for the US health system:
terminology systems (SNOMED CT US, ICD-10-CM, LOINC, ATC), FHIR profiles
from US Core IG, extensions, identifier systems, system prompt,
tool descriptions, and tool enum values.
"""

from __future__ import annotations

from saludai_core.locales._prompt_builder import build_fhir_awareness_section
from saludai_core.locales._types import (
    ExtensionDef,
    FHIRProfileDef,
    IdentifierSystemDef,
    LocalePack,
    LocaleResourceConfig,
    QueryPattern,
    ResourceRelationship,
    TerminologySystemDef,
)
from saludai_core.locales.en_us._prompt import SYSTEM_PROMPT_EN_US

# ---------------------------------------------------------------------------
# Terminology system definitions
# ---------------------------------------------------------------------------

SNOMED_CT_US = TerminologySystemDef(
    key="snomed_ct",
    system_uri="http://snomed.info/sct",
    csv_filename="snomed_en_us.csv",
    display_name="SNOMED CT US Edition",
    data_package="saludai_core.locales.en_us",
)

ICD_10_CM = TerminologySystemDef(
    key="icd_10_cm",
    system_uri="http://hl7.org/fhir/sid/icd-10-cm",
    csv_filename="icd10_cm.csv",
    display_name="ICD-10-CM",
    data_package="saludai_core.locales.en_us",
)

LOINC_DEF = TerminologySystemDef(
    key="loinc",
    system_uri="http://loinc.org",
    csv_filename="loinc_en.csv",
    display_name="LOINC",
    data_package="saludai_core.locales.en_us",
)

ATC_DEF = TerminologySystemDef(
    key="atc",
    system_uri="http://www.whocc.no/atc",
    csv_filename="atc_en.csv",
    display_name="ATC (Anatomical Therapeutic Chemical)",
    data_package="saludai_core.locales.en_us",
)

# ---------------------------------------------------------------------------
# Extensions (US Core IG)
# ---------------------------------------------------------------------------

_EXT_RACE = ExtensionDef(
    url="http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
    name="Race",
    description="Patient's race (OMB categories)",
    value_type="complex",
    context="Patient",
)

_EXT_ETHNICITY = ExtensionDef(
    url="http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
    name="Ethnicity",
    description="Patient's ethnicity (Hispanic or Latino / Not Hispanic or Latino)",
    value_type="complex",
    context="Patient",
)

_EXT_BIRTH_SEX = ExtensionDef(
    url="http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex",
    name="Birth Sex",
    description="Patient's sex assigned at birth (M, F, UNK)",
    value_type="code",
    context="Patient",
)

_EXTENSIONS = (
    _EXT_RACE,
    _EXT_ETHNICITY,
    _EXT_BIRTH_SEX,
)

# ---------------------------------------------------------------------------
# FHIR Profiles (US Core IG)
# ---------------------------------------------------------------------------

_US_CORE_BASE = "http://hl7.org/fhir/us/core/StructureDefinition"

_PROFILES = (
    FHIRProfileDef(
        resource_type="Patient",
        profile_url=f"{_US_CORE_BASE}/us-core-patient",
        name="US Core Patient",
        description=(
            "US Core Patient with race, ethnicity, birth sex extensions. "
            "Requires name, gender, identifier"
        ),
        mandatory_extensions=(
            _EXT_RACE,
            _EXT_ETHNICITY,
            _EXT_BIRTH_SEX,
        ),
    ),
    FHIRProfileDef(
        resource_type="Encounter",
        profile_url=f"{_US_CORE_BASE}/us-core-encounter",
        name="US Core Encounter",
        description="Clinical encounter with type, status, period, and class",
    ),
    FHIRProfileDef(
        resource_type="Condition",
        profile_url=f"{_US_CORE_BASE}/us-core-condition-problems-health-concerns",
        name="US Core Condition",
        description="Problems and health concerns with SNOMED CT or ICD-10-CM coding",
    ),
    FHIRProfileDef(
        resource_type="Observation",
        profile_url=f"{_US_CORE_BASE}/us-core-observation-lab",
        name="US Core Laboratory Result",
        description="Lab results with LOINC coding and reference ranges",
    ),
    FHIRProfileDef(
        resource_type="MedicationRequest",
        profile_url=f"{_US_CORE_BASE}/us-core-medicationrequest",
        name="US Core MedicationRequest",
        description="Medication prescriptions with coded medication reference",
    ),
    FHIRProfileDef(
        resource_type="Procedure",
        profile_url=f"{_US_CORE_BASE}/us-core-procedure",
        name="US Core Procedure",
        description="Surgical and diagnostic procedures with SNOMED CT coding",
    ),
    FHIRProfileDef(
        resource_type="AllergyIntolerance",
        profile_url=f"{_US_CORE_BASE}/us-core-allergyintolerance",
        name="US Core AllergyIntolerance",
        description="Allergies and intolerances with clinical status and reaction",
    ),
    FHIRProfileDef(
        resource_type="DiagnosticReport",
        profile_url=f"{_US_CORE_BASE}/us-core-diagnosticreport-lab",
        name="US Core DiagnosticReport for Laboratory",
        description="Lab reports with LOINC coding and result references",
    ),
    FHIRProfileDef(
        resource_type="Immunization",
        profile_url=f"{_US_CORE_BASE}/us-core-immunization",
        name="US Core Immunization",
        description="Vaccination records with CVX coding",
    ),
)

# ---------------------------------------------------------------------------
# Identifier systems
# ---------------------------------------------------------------------------

_IDENTIFIER_SYSTEMS = (
    IdentifierSystemDef(
        system_uri="http://hl7.org/fhir/sid/us-ssn",
        name="SSN",
        description="Social Security Number",
        resource_types=("Patient",),
    ),
    IdentifierSystemDef(
        system_uri="http://hl7.org/fhir/sid/us-npi",
        name="NPI",
        description="National Provider Identifier",
        resource_types=("Practitioner", "Organization"),
    ),
    IdentifierSystemDef(
        system_uri="http://hospital.example.org/mrn",
        name="MRN",
        description="Medical Record Number (facility-specific)",
        resource_types=("Patient",),
    ),
)

# ---------------------------------------------------------------------------
# Resource configs
# ---------------------------------------------------------------------------

_RESOURCE_CONFIGS = (
    LocaleResourceConfig(
        resource_type="Patient",
        usage_note="Demographics with race, ethnicity, birth sex extensions",
        common_search_params=(
            "identifier",
            "name",
            "family",
            "given",
            "birthdate",
            "gender",
            "address-state",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Practitioner",
        usage_note="Healthcare providers identified by NPI",
        common_search_params=("identifier", "name", "active"),
    ),
    LocaleResourceConfig(
        resource_type="Organization",
        usage_note="Healthcare organizations identified by NPI",
        common_search_params=("identifier", "name", "address-state", "type"),
    ),
    LocaleResourceConfig(
        resource_type="Condition",
        usage_note="Diagnoses coded with SNOMED CT US or ICD-10-CM",
        common_search_params=(
            "code",
            "subject",
            "clinical-status",
            "onset-date",
            "category",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Observation",
        usage_note="Lab results (LOINC), vital signs",
        common_search_params=(
            "code",
            "subject",
            "date",
            "category",
            "value-quantity",
        ),
    ),
    LocaleResourceConfig(
        resource_type="MedicationRequest",
        usage_note="Prescriptions with ATC code (system http://www.whocc.no/atc)",
        common_search_params=(
            "code",
            "subject",
            "status",
            "authoredon",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Immunization",
        usage_note="Vaccination records",
        common_search_params=(
            "vaccine-code",
            "patient",
            "date",
            "status",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Encounter",
        usage_note="Clinical encounters and visits",
        common_search_params=(
            "subject",
            "date",
            "class",
            "status",
            "type",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Procedure",
        usage_note="Surgical and diagnostic procedures (SNOMED CT)",
        common_search_params=(
            "code",
            "subject",
            "date",
            "status",
        ),
    ),
    LocaleResourceConfig(
        resource_type="AllergyIntolerance",
        usage_note="Confirmed allergies and intolerances",
        common_search_params=(
            "code",
            "patient",
            "clinical-status",
            "category",
        ),
    ),
    LocaleResourceConfig(
        resource_type="DiagnosticReport",
        usage_note="Lab reports and diagnostic studies (LOINC)",
        common_search_params=(
            "code",
            "subject",
            "date",
            "status",
            "category",
        ),
    ),
    LocaleResourceConfig(
        resource_type="CarePlan",
        usage_note=(
            "Care plans for chronic conditions (diabetes, hypertension, asthma, etc.). "
            "Linked to Condition via addresses"
        ),
        common_search_params=(
            "subject",
            "status",
            "category",
            "date",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Validation notes
# ---------------------------------------------------------------------------

_VALIDATION_NOTES = """\
- Patient: US Core requires name, gender, and at least one identifier
- Patient: race and ethnicity extensions are must-support
- Observation: LOINC code required for lab results
- MedicationRequest: coded medication is required\
"""

# ---------------------------------------------------------------------------
# Resource relationship graph (ADR-009)
# ---------------------------------------------------------------------------

_RESOURCE_RELATIONSHIPS = (
    ResourceRelationship(source="Condition", target="Patient", search_param="subject"),
    ResourceRelationship(source="Observation", target="Patient", search_param="subject"),
    ResourceRelationship(source="MedicationRequest", target="Patient", search_param="subject"),
    ResourceRelationship(source="Encounter", target="Patient", search_param="subject"),
    ResourceRelationship(source="Procedure", target="Patient", search_param="subject"),
    ResourceRelationship(source="DiagnosticReport", target="Patient", search_param="subject"),
    ResourceRelationship(source="AllergyIntolerance", target="Patient", search_param="patient"),
    ResourceRelationship(source="Immunization", target="Patient", search_param="patient"),
    ResourceRelationship(source="CarePlan", target="Patient", search_param="subject"),
    ResourceRelationship(source="CarePlan", target="Condition", search_param="addresses"),
)

# ---------------------------------------------------------------------------
# Query pattern catalog (ADR-009)
# ---------------------------------------------------------------------------

_QUERY_PATTERNS = (
    QueryPattern(
        name="count_simple",
        description="Count resources of a type without filters",
        template="{resource_type}?_summary=count",
        example_question="How many patients are there in total?",
        example_query="Patient?_summary=count",
        allowed_tools=("count_fhir",),
    ),
    QueryPattern(
        name="count_filtered",
        description="Count resources of a type with direct filters on that resource",
        template="{resource_type}?{params}&_summary=count",
        example_question="How many patients are in New York?",
        example_query="Patient?address-state=New%20York&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="count_with_condition",
        description="Count patients who have a specific condition/diagnosis",
        template="Patient?_has:Condition:subject:code={code}&_summary=count",
        example_question="How many patients have type 2 diabetes?",
        example_query="Patient?_has:Condition:subject:code=http://snomed.info/sct|44054006&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="count_with_resource",
        description=(
            "Count patients who have an associated resource "
            "(medication, vaccine, procedure, etc.)"
        ),
        template="Patient?_has:{source}:{search_param}:code={code}&_summary=count",
        example_question="How many patients take metformin?",
        example_query="Patient?_has:MedicationRequest:subject:code=http://www.whocc.no/atc|A10BA02&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="count_cross_filter",
        description="Count patients with demographic filter + associated condition/resource",
        template="Patient?{patient_filter}&_has:{source}:{search_param}:code={code}&_summary=count",
        example_question="How many patients with type 2 diabetes live in New York?",
        example_query="Patient?address-state=New%20York&_has:Condition:subject:code=http://snomed.info/sct|44054006&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="search_include",
        description="Search resources and include referenced resources in the same response",
        template="{resource_type}?{params}&_include={resource_type}:{search_param}",
        example_question="Diabetes conditions with patient data",
        example_query="Condition?code=http://snomed.info/sct|44054006&_include=Condition:subject",
        allowed_tools=(
            "resolve_terminology",
            "search_fhir",
            "get_resource",
            "execute_code",
        ),
    ),
    QueryPattern(
        name="search_aggregate",
        description="Search data to compute averages, distributions, or rankings with execute_code",
        template="{resource_type}?{params} -> execute_code for calculation",
        example_question="What is the average HbA1c in patients with diabetes?",
        example_query="Observation?code=http://loinc.org|4548-4 -> execute_code: statistics.mean()",
        allowed_tools=(
            "resolve_terminology",
            "search_fhir",
            "execute_code",
        ),
    ),
    QueryPattern(
        name="multi_search",
        description=(
            "Correlation or negation: search 2+ resources and "
            "cross-reference with execute_code"
        ),
        template="search A + search B -> execute_code intersect/diff",
        example_question="Patients with T2DM who are NOT on metformin",
        example_query=(
            "1) Condition?code=T2DM 2) MedicationRequest?code=met 3) execute_code: set_a - set_b"
        ),
        # All tools — complex queries need maximum flexibility
        allowed_tools=(),
    ),
    QueryPattern(
        name="temporal",
        description="Filter resources by date range",
        template="{resource_type}?date=ge{start}&date=le{end}",
        example_question="How many encounters were there in 2024?",
        example_query="Encounter?date=ge2024-01-01&date=le2024-12-31&_summary=count",
        allowed_tools=(
            "resolve_terminology",
            "search_fhir",
            "count_fhir",
            "execute_code",
        ),
    ),
    QueryPattern(
        name="list_resources",
        description="List individual resources with their full details",
        template="{resource_type}?{params}",
        example_question="What medications does patient 1005 have?",
        example_query="MedicationRequest?subject=Patient/1005",
        allowed_tools=(
            "resolve_terminology",
            "search_fhir",
            "get_resource",
            "execute_code",
        ),
    ),
    QueryPattern(
        name="careplan_query",
        description=(
            "Search or count care plans, optionally filtered "
            "by status, patient, or associated condition"
        ),
        template="CarePlan?{params}",
        example_question="How many active care plans are there?",
        example_query="CarePlan?status=active&_summary=count",
        allowed_tools=(
            "resolve_terminology",
            "search_fhir",
            "count_fhir",
            "execute_code",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Tool descriptions (English)
# ---------------------------------------------------------------------------

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "resolve_terminology": (
        "Resolves a clinical term in natural language to a standard code "
        "(SNOMED CT, ICD-10-CM, LOINC, or ATC for medications). Use this tool "
        "ALWAYS before searching with medical terms to get the correct code."
    ),
    "search_fhir": (
        "Executes a search on the FHIR R4 server. Returns a summary "
        "of the result Bundle with the most relevant fields of each resource."
    ),
    "get_resource": (
        "Reads an individual FHIR resource by type and ID. "
        "Use this tool to get the full details of a specific resource "
        "when you already have its reference (e.g., Patient/1005)."
    ),
    "execute_code": (
        "Executes Python code to process and analyze data. "
        "Use this tool when you need to count, group, filter, or "
        "calculate over data obtained from FHIR searches. "
        "Available modules: json, collections (Counter, defaultdict), "
        "datetime, math, statistics, re. Use print() to show results."
    ),
    "count_fhir": (
        "Counts FHIR resources on the server without transferring data. "
        "Uses _summary=count to get only the total. "
        "Supports _has for cross-resource counts (e.g., count patients with a condition). "
        "Ideal for 'how many' questions."
    ),
}

# ---------------------------------------------------------------------------
# EN_US Locale Pack
# ---------------------------------------------------------------------------


def _build_en_us_pack() -> LocalePack:
    """Build the EN_US locale pack with dynamic FHIR awareness prompt."""
    # First pass: build pack with all metadata to feed the prompt builder.
    pack = LocalePack(
        code="en_us",
        name="United States",
        language="en",
        terminology_systems=(SNOMED_CT_US, ICD_10_CM, LOINC_DEF, ATC_DEF),
        system_prompt="",  # placeholder
        tool_descriptions=_TOOL_DESCRIPTIONS,
        tool_system_enum=("snomed_ct", "icd_10_cm", "loinc", "atc"),
        fhir_profiles=_PROFILES,
        extensions=_EXTENSIONS,
        identifier_systems=_IDENTIFIER_SYSTEMS,
        resource_configs=_RESOURCE_CONFIGS,
        validation_notes=_VALIDATION_NOTES,
        resource_relationships=_RESOURCE_RELATIONSHIPS,
        query_patterns=_QUERY_PATTERNS,
    )
    # Generate awareness section from metadata and append to base prompt.
    awareness = build_fhir_awareness_section(pack)
    full_prompt = SYSTEM_PROMPT_EN_US + awareness
    # Rebuild with the full prompt (frozen dataclass — can't mutate).
    return LocalePack(
        code=pack.code,
        name=pack.name,
        language=pack.language,
        terminology_systems=pack.terminology_systems,
        system_prompt=full_prompt,
        tool_descriptions=pack.tool_descriptions,
        tool_system_enum=pack.tool_system_enum,
        fhir_profiles=pack.fhir_profiles,
        extensions=pack.extensions,
        custom_operations=pack.custom_operations,
        custom_search_params=pack.custom_search_params,
        identifier_systems=pack.identifier_systems,
        resource_configs=pack.resource_configs,
        validation_notes=pack.validation_notes,
        resource_relationships=pack.resource_relationships,
        query_patterns=pack.query_patterns,
    )


EN_US_LOCALE_PACK = _build_en_us_pack()
