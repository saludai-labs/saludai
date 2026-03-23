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
    QueryPattern,
    ResourceRelationship,
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

ATC_DEF = TerminologySystemDef(
    key="atc",
    system_uri="http://www.whocc.no/atc",
    csv_filename="atc.csv",
    display_name="ATC (Anatomical Therapeutic Chemical)",
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
        usage_note="Prescripciones con codigo ATC (sistema http://www.whocc.no/atc)",
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
    LocaleResourceConfig(
        resource_type="Procedure",
        usage_note="Procedimientos quirurgicos y diagnosticos (SNOMED CT)",
        common_search_params=(
            "code",
            "subject",
            "date",
            "status",
        ),
    ),
    LocaleResourceConfig(
        resource_type="AllergyIntolerance",
        usage_note="Alergias e intolerancias confirmadas",
        common_search_params=(
            "code",
            "patient",
            "clinical-status",
            "category",
        ),
    ),
    LocaleResourceConfig(
        resource_type="DiagnosticReport",
        usage_note="Informes de laboratorio y estudios diagnosticos (LOINC)",
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
            "Planes de cuidado para condiciones cronicas (diabetes, hipertension, asma, etc.). "
            "Vinculados a Condition via addresses"
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
- Patient: requiere al menos 1 identifier con DNI (system http://www.renaper.gob.ar/dni)
- Patient: name.family y name.given son obligatorios
- Patient: gender y birthDate son obligatorios en el perfil Federador
- Immunization: requiere extension NomivacEsquema en protocolApplied
- Practitioner: identifier REFEPS recomendado para profesionales matriculados\
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
        description="Contar recursos de un tipo sin filtros",
        template="{resource_type}?_summary=count",
        example_question="Cuantos pacientes hay en total?",
        example_query="Patient?_summary=count",
        allowed_tools=("count_fhir",),
    ),
    QueryPattern(
        name="count_filtered",
        description="Contar recursos de un tipo con filtros directos sobre ese recurso",
        template="{resource_type}?{params}&_summary=count",
        example_question="Cuantos pacientes hay en Buenos Aires?",
        example_query="Patient?address-state=Buenos%20Aires&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="count_with_condition",
        description="Contar pacientes que tienen una condicion/diagnostico especifico",
        template="Patient?_has:Condition:subject:code={code}&_summary=count",
        example_question="Cuantos pacientes tienen diabetes tipo 2?",
        example_query="Patient?_has:Condition:subject:code=http://snomed.info/sct|44054006&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="count_with_resource",
        description=(
            "Contar pacientes que tienen un recurso asociado "
            "(medicamento, vacuna, procedimiento, etc.)"
        ),
        template="Patient?_has:{source}:{search_param}:code={code}&_summary=count",
        example_question="Cuantos pacientes toman metformina?",
        example_query="Patient?_has:MedicationRequest:subject:code=http://www.whocc.no/atc|A10BA02&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="count_cross_filter",
        description="Contar pacientes con filtro demografico + condicion/recurso asociado",
        template="Patient?{patient_filter}&_has:{source}:{search_param}:code={code}&_summary=count",
        example_question="Cuantos pacientes con diabetes tipo 2 viven en Buenos Aires?",
        example_query="Patient?address-state=Buenos%20Aires&_has:Condition:subject:code=http://snomed.info/sct|44054006&_summary=count",
        allowed_tools=("resolve_terminology", "count_fhir"),
    ),
    QueryPattern(
        name="search_include",
        description="Buscar recursos e incluir recursos referenciados en la misma respuesta",
        template="{resource_type}?{params}&_include={resource_type}:{search_param}",
        example_question="Condiciones de diabetes con datos del paciente",
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
        description=(
            "Buscar datos para calcular promedios, distribuciones o rankings con execute_code"
        ),
        template="{resource_type}?{params} -> execute_code para calcular",
        example_question="Cual es el promedio de HbA1c en pacientes con diabetes?",
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
            "Correlacion o negacion: buscar en 2+ recursos y cruzar resultados con execute_code"
        ),
        template="search A + search B -> execute_code intersect/diff",
        example_question="Pacientes con DM2 que NO toman metformina",
        example_query=(
            "1) Condition?code=DM2 2) MedicationRequest?code=met 3) execute_code: set_a - set_b"
        ),
        # All tools — complex queries need maximum flexibility
        allowed_tools=(),
    ),
    QueryPattern(
        name="temporal",
        description="Filtrar recursos por rango de fechas",
        template="{resource_type}?date=ge{start}&date=le{end}",
        example_question="Cuantos encuentros hubo en 2024?",
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
        description="Listar recursos individuales con sus detalles completos",
        template="{resource_type}?{params}",
        example_question="Que medicamentos tiene prescriptos el paciente 1005?",
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
            "Buscar o contar planes de cuidado, opcionalmente filtrados "
            "por estado, paciente o condicion asociada"
        ),
        template="CarePlan?{params}",
        example_question="Cuantos planes de cuidado activos hay?",
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
# Tool descriptions (Spanish - Argentina)
# ---------------------------------------------------------------------------

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "resolve_terminology": (
        "Resuelve un termino clinico en lenguaje natural a un codigo estandar "
        "(SNOMED CT, CIE-10, LOINC, o ATC para medicamentos). Usa esta herramienta "
        "SIEMPRE antes de buscar con terminos medicos para obtener el codigo correcto."
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
    "count_fhir": (
        "Cuenta recursos FHIR en el servidor sin transferir datos. "
        "Usa _summary=count para obtener solo el total. "
        "Soporta _has para conteos cross-resource (ej: contar pacientes con una condicion). "
        "Ideal para preguntas de 'cuantos hay'."
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
        terminology_systems=(SNOMED_CT_AR, CIE_10_AR, LOINC_DEF, ATC_DEF),
        system_prompt="",  # placeholder
        tool_descriptions=_TOOL_DESCRIPTIONS,
        tool_system_enum=("snomed_ct", "cie_10", "loinc", "atc"),
        fhir_profiles=_PROFILES,
        extensions=_EXTENSIONS,
        custom_operations=_CUSTOM_OPERATIONS,
        custom_search_params=_CUSTOM_SEARCH_PARAMS,
        identifier_systems=_IDENTIFIER_SYSTEMS,
        resource_configs=_RESOURCE_CONFIGS,
        validation_notes=_VALIDATION_NOTES,
        resource_relationships=_RESOURCE_RELATIONSHIPS,
        query_patterns=_QUERY_PATTERNS,
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
        resource_relationships=pack.resource_relationships,
        query_patterns=pack.query_patterns,
    )


AR_LOCALE_PACK = _build_ar_pack()
