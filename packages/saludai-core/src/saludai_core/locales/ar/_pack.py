"""Argentina locale pack definition.

Bundles all locale-specific configuration for the Argentine health system:
terminology systems (SNOMED CT AR, CIE-10 AR, LOINC), FHIR profiles from
AR.FHIR.CORE / openRSD, extensions, identifier systems, system prompt,
tool descriptions, and tool enum values.
"""

from __future__ import annotations

from saludai_core.locales._prompt_builder import build_fhir_awareness_section
from saludai_core.locales._types import (
    CustomOperationDef,
    CustomSearchParamDef,
    ExtensionDef,
    FHIRProfileDef,
    IdentifierSystemDef,
    LocalePack,
    LocaleResourceConfig,
    TerminologySystemDef,
)
from saludai_core.locales.ar._prompt import SYSTEM_PROMPT_AR

# ---------------------------------------------------------------------------
# Terminology system definitions
# ---------------------------------------------------------------------------

SNOMED_CT_AR = TerminologySystemDef(
    key="snomed_ct",
    system_uri="http://snomed.info/sct",
    csv_filename="snomed_ar.csv",
    display_name="SNOMED CT edicion argentina",
    data_package="saludai_core.locales.ar",
)

CIE_10_AR = TerminologySystemDef(
    key="cie_10",
    system_uri="http://hl7.org/fhir/sid/icd-10",
    csv_filename="cie10_ar.csv",
    display_name="CIE-10 adaptacion argentina",
    data_package="saludai_core.locales.ar",
)

LOINC_DEF = TerminologySystemDef(
    key="loinc",
    system_uri="http://loinc.org",
    csv_filename="loinc.csv",
    display_name="LOINC",
    data_package="saludai_core.locales.ar",
)

# ---------------------------------------------------------------------------
# Extensions (AR.FHIR.CORE / openRSD)
# ---------------------------------------------------------------------------

_EXT_ETNIA = ExtensionDef(
    url="http://fhir.msal.gov.ar/StructureDefinition/Etnia",
    name="Etnia",
    description="Grupo etnico del paciente (codificado SNOMED CT AR)",
    value_type="CodeableConcept",
    context="Patient",
)

_EXT_FATHERS_FAMILY = ExtensionDef(
    url="http://hl7.org/fhir/StructureDefinition/humanname-fathers-family",
    name="Apellido paterno",
    description="Primer apellido (componente paterno) del nombre",
    value_type="string",
    context="Patient.name.family",
)

_EXT_MOTHERS_FAMILY = ExtensionDef(
    url="http://hl7.org/fhir/StructureDefinition/humanname-mothers-family",
    name="Apellido materno",
    description="Segundo apellido (componente materno) del nombre",
    value_type="string",
    context="Patient.name.family",
)

_EXT_GENDER_IDENTITY = ExtensionDef(
    url="http://hl7.org/fhir/StructureDefinition/patient-genderIdentity",
    name="Identidad de genero",
    description="Identidad de genero autopercibida (Ley 26.743)",
    value_type="CodeableConcept",
    context="Patient",
)

_EXT_BIRTH_PLACE = ExtensionDef(
    url="http://hl7.org/fhir/StructureDefinition/patient-birthPlace",
    name="Lugar de nacimiento",
    description="Direccion del lugar de nacimiento del paciente",
    value_type="Address",
    context="Patient",
)

_EXT_NOMIVAC_ESQUEMA = ExtensionDef(
    url="http://fhir.msal.gov.ar/StructureDefinition/NomivacEsquema",
    name="Esquema NOMIVAC",
    description="Codigo de esquema de vacunacion del calendario nacional",
    value_type="Coding",
    context="Immunization.protocolApplied.series",
)

_EXT_MATRICULA_HABILITADA = ExtensionDef(
    url="http://fhir.msal.gob.ar/StructureDefinition/MatriculaHabilitada",
    name="Matricula habilitada",
    description="Indica si la matricula del profesional esta activa",
    value_type="boolean",
    context="Practitioner.qualification",
)

# All extensions
_EXTENSIONS = (
    _EXT_ETNIA,
    _EXT_FATHERS_FAMILY,
    _EXT_MOTHERS_FAMILY,
    _EXT_GENDER_IDENTITY,
    _EXT_BIRTH_PLACE,
    _EXT_NOMIVAC_ESQUEMA,
    _EXT_MATRICULA_HABILITADA,
)

# ---------------------------------------------------------------------------
# FHIR Profiles (AR.FHIR.CORE)
# ---------------------------------------------------------------------------

_BASE_URL = "http://fhir.msal.gov.ar/core/StructureDefinition"

_PROFILES = (
    FHIRProfileDef(
        resource_type="Patient",
        profile_url=f"{_BASE_URL}/Patient-ar-core",
        name="Paciente AR Core",
        description=(
            "Perfil argentino con DNI obligatorio, apellido paterno/materno, "
            "etnia, identidad de genero, lugar de nacimiento"
        ),
        mandatory_extensions=(
            _EXT_FATHERS_FAMILY,
            _EXT_MOTHERS_FAMILY,
        ),
    ),
    FHIRProfileDef(
        resource_type="Practitioner",
        profile_url=f"{_BASE_URL}/Practitioner-ar-core",
        name="Profesional AR Core",
        description=("Perfil argentino con matricula REFEPS, estado de habilitacion, especialidad"),
        mandatory_extensions=(_EXT_MATRICULA_HABILITADA,),
    ),
    FHIRProfileDef(
        resource_type="Organization",
        profile_url=f"{_BASE_URL}/Organization-ar-core",
        name="Organizacion AR Core",
        description=("Establecimiento de salud con identificador REFES (codigo de 14 digitos)"),
    ),
    FHIRProfileDef(
        resource_type="Location",
        profile_url=f"{_BASE_URL}/Location-ar-core",
        name="Ubicacion AR Core",
        description="Ubicacion fisica de un establecimiento de salud",
    ),
    FHIRProfileDef(
        resource_type="Immunization",
        profile_url=f"{_BASE_URL}/Immunization-ar-core",
        name="Inmunizacion AR Core",
        description=("Registro de vacunacion con esquema NOMIVAC y codigos SNOMED CT AR"),
        mandatory_extensions=(_EXT_NOMIVAC_ESQUEMA,),
    ),
    FHIRProfileDef(
        resource_type="Composition",
        profile_url="http://fhir.msal.gov.ar/StructureDefinition/Composition_ar_ips",
        name="Composicion IPS Argentina",
        description=(
            "Resumen de paciente (IPS) argentino con seccion obligatoria de inmunizaciones"
        ),
    ),
)

# ---------------------------------------------------------------------------
# Identifier systems
# ---------------------------------------------------------------------------

_IDENTIFIER_SYSTEMS = (
    IdentifierSystemDef(
        system_uri="http://www.renaper.gob.ar/dni",
        name="DNI",
        description="Documento Nacional de Identidad (RENAPER)",
        resource_types=("Patient",),
    ),
    IdentifierSystemDef(
        system_uri="https://sisa.msal.gov.ar/REFEPS",
        name="REFEPS",
        description="Registro Federal de Profesionales de Salud",
        resource_types=("Practitioner",),
    ),
    IdentifierSystemDef(
        system_uri="http://argentina.gob.ar/salud/refes",
        name="REFES",
        description="Registro Federal de Establecimientos de Salud (codigo 14 digitos)",
        resource_types=("Organization",),
    ),
)

# ---------------------------------------------------------------------------
# Custom operations
# ---------------------------------------------------------------------------

_CUSTOM_OPERATIONS = (
    CustomOperationDef(
        name="$summary",
        resource_type="Patient",
        description="Genera un resumen IPS (International Patient Summary) del paciente",
    ),
)

# ---------------------------------------------------------------------------
# Custom search parameters (AR-specific)
# ---------------------------------------------------------------------------

_CUSTOM_SEARCH_PARAMS = (
    CustomSearchParamDef(
        name="edad",
        resource_type="Patient",
        description="Edad calculada del paciente (no nativo FHIR, usar birthdate en su lugar)",
        expression="",
    ),
    CustomSearchParamDef(
        name="provincia",
        resource_type="Patient",
        description="Provincia de residencia (equivale a address-state con codigos INDEC)",
        expression="Patient.address.state",
    ),
    CustomSearchParamDef(
        name="cobertura",
        resource_type="Patient",
        description="Obra social o prepaga del paciente (buscar via Coverage.beneficiary)",
        expression="",
    ),
    CustomSearchParamDef(
        name="esquema-nomivac",
        resource_type="Immunization",
        description="Esquema de vacunacion NOMIVAC (extension NomivacEsquema)",
        expression="Immunization.protocolApplied.series",
    ),
)

# ---------------------------------------------------------------------------
# Resource configs
# ---------------------------------------------------------------------------

_RESOURCE_CONFIGS = (
    LocaleResourceConfig(
        resource_type="Patient",
        usage_note=(
            "Datos demograficos con DNI obligatorio. Puede incluir CUIL, etnia, identidad de genero"
        ),
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
        usage_note="Profesionales de salud registrados en REFEPS con matricula",
        common_search_params=("identifier", "name", "active"),
    ),
    LocaleResourceConfig(
        resource_type="Organization",
        usage_note="Establecimientos de salud registrados en REFES",
        common_search_params=("identifier", "name", "address-state", "type"),
    ),
    LocaleResourceConfig(
        resource_type="Condition",
        usage_note="Diagnosticos codificados con SNOMED CT AR o CIE-10",
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
        usage_note="Resultados de laboratorio (LOINC), signos vitales",
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
        usage_note="Prescripciones con codigo SNOMED CT o texto libre",
        common_search_params=(
            "code",
            "subject",
            "status",
            "authoredon",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Immunization",
        usage_note="Vacunaciones del calendario nacional (NOMIVAC)",
        common_search_params=(
            "vaccine-code",
            "patient",
            "date",
            "status",
        ),
    ),
    LocaleResourceConfig(
        resource_type="Encounter",
        usage_note="Consultas y encuentros clinicos",
        common_search_params=(
            "subject",
            "date",
            "class",
            "status",
            "type",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Validation notes
# ---------------------------------------------------------------------------

_VALIDATION_NOTES = """\
- Patient: requiere al menos 1 identifier con DNI (system http://www.renaper.gob.ar/dni)
- Patient: name.family y name.given son obligatorios
- Patient: gender y birthDate son obligatorios en el perfil Federador
- Immunization: requiere extension NomivacEsquema en protocolApplied
- Practitioner: identifier REFEPS recomendado para profesionales matriculados\
"""

# ---------------------------------------------------------------------------
# Tool descriptions (Spanish - Argentina)
# ---------------------------------------------------------------------------

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "resolve_terminology": (
        "Resuelve un termino clinico en lenguaje natural a un codigo estandar "
        "(SNOMED CT, CIE-10, o LOINC). Usa esta herramienta SIEMPRE antes de "
        "buscar con terminos medicos para obtener el codigo correcto."
    ),
    "search_fhir": (
        "Ejecuta una busqueda en el servidor FHIR R4. Devuelve un resumen "
        "del Bundle de resultados con los campos mas relevantes de cada recurso."
    ),
    "get_resource": (
        "Lee un recurso FHIR individual por tipo e ID. "
        "Usa esta herramienta para obtener detalles completos de un recurso "
        "especifico cuando ya tenes su referencia (ej: Patient/1005)."
    ),
    "execute_code": (
        "Ejecuta codigo Python para procesar y analizar datos. "
        "Usa esta herramienta cuando necesites contar, agrupar, filtrar o "
        "calcular sobre los datos obtenidos de busquedas FHIR. "
        "Modulos disponibles: json, collections (Counter, defaultdict), "
        "datetime, math, statistics, re. Usa print() para mostrar resultados."
    ),
}

# ---------------------------------------------------------------------------
# AR Locale Pack
# ---------------------------------------------------------------------------


def _build_ar_pack() -> LocalePack:
    """Build the AR locale pack with dynamic FHIR awareness prompt."""
    # First pass: build pack with all metadata to feed the prompt builder.
    pack = LocalePack(
        code="ar",
        name="Argentina",
        language="es",
        terminology_systems=(SNOMED_CT_AR, CIE_10_AR, LOINC_DEF),
        system_prompt="",  # placeholder
        tool_descriptions=_TOOL_DESCRIPTIONS,
        tool_system_enum=("snomed_ct", "cie_10", "loinc"),
        fhir_profiles=_PROFILES,
        extensions=_EXTENSIONS,
        custom_operations=_CUSTOM_OPERATIONS,
        custom_search_params=_CUSTOM_SEARCH_PARAMS,
        identifier_systems=_IDENTIFIER_SYSTEMS,
        resource_configs=_RESOURCE_CONFIGS,
        validation_notes=_VALIDATION_NOTES,
    )
    # Generate awareness section from metadata and append to base prompt.
    awareness = build_fhir_awareness_section(pack)
    full_prompt = SYSTEM_PROMPT_AR + awareness
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
    )


AR_LOCALE_PACK = _build_ar_pack()
