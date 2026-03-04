"""Argentina locale pack definition.

Bundles all locale-specific configuration for the Argentine health system:
terminology systems (SNOMED CT AR, CIE-10 AR, LOINC), system prompt,
tool descriptions, and tool enum values.
"""

from __future__ import annotations

from saludai_core.locales._types import LocalePack, TerminologySystemDef
from saludai_core.locales.ar._prompt import SYSTEM_PROMPT_AR

# ---------------------------------------------------------------------------
# Terminology system definitions
# ---------------------------------------------------------------------------

SNOMED_CT_AR = TerminologySystemDef(
    key="snomed_ct",
    system_uri="http://snomed.info/sct",
    csv_filename="snomed_ar.csv",
    display_name="SNOMED CT edición argentina",
    data_package="saludai_core.locales.ar",
)

CIE_10_AR = TerminologySystemDef(
    key="cie_10",
    system_uri="http://hl7.org/fhir/sid/icd-10",
    csv_filename="cie10_ar.csv",
    display_name="CIE-10 adaptación argentina",
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
# Tool descriptions (Spanish — Argentina)
# ---------------------------------------------------------------------------

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "resolve_terminology": (
        "Resuelve un término clínico en lenguaje natural a un código estándar "
        "(SNOMED CT, CIE-10, o LOINC). Usá esta herramienta SIEMPRE antes de "
        "buscar con términos médicos para obtener el código correcto."
    ),
    "search_fhir": (
        "Ejecuta una búsqueda en el servidor FHIR R4. Devuelve un resumen "
        "del Bundle de resultados con los campos más relevantes de cada recurso."
    ),
    "get_resource": (
        "Lee un recurso FHIR individual por tipo e ID. "
        "Usá esta herramienta para obtener detalles completos de un recurso "
        "específico cuando ya tenés su referencia (ej: Patient/1005)."
    ),
    "execute_code": (
        "Ejecuta código Python para procesar y analizar datos. "
        "Usá esta herramienta cuando necesites contar, agrupar, filtrar o "
        "calcular sobre los datos obtenidos de búsquedas FHIR. "
        "Módulos disponibles: json, collections (Counter, defaultdict), "
        "datetime, math, statistics, re. Usá print() para mostrar resultados."
    ),
}

# ---------------------------------------------------------------------------
# AR Locale Pack
# ---------------------------------------------------------------------------

AR_LOCALE_PACK = LocalePack(
    code="ar",
    name="Argentina",
    language="es",
    terminology_systems=(SNOMED_CT_AR, CIE_10_AR, LOINC_DEF),
    system_prompt=SYSTEM_PROMPT_AR,
    tool_descriptions=_TOOL_DESCRIPTIONS,
    tool_system_enum=("snomed_ct", "cie_10", "loinc"),
)
