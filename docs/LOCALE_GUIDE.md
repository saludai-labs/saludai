# Guia de Locale Packs

> Como crear un locale pack para extender SaludAI a tu pais/region.

## Que es un Locale Pack?

Un locale pack contiene toda la configuracion especifica de un pais o region:

- **Sistemas de terminologia**: que CSVs de SNOMED CT, CIE-10, LOINC u otros usar
- **System prompt**: el prompt completo del agente, localizado
- **Descripciones de tools**: texto que el LLM ve para cada herramienta
- **Enum de sistemas**: valores validos para el parametro `system` de `resolve_terminology`
- **Perfiles FHIR**: profiles definidos por la guia de implementacion local
- **Extensiones FHIR**: extensions custom del pais/region
- **Sistemas de identificacion**: DNI, CUIL, REFEPS, etc.
- **Operaciones custom**: operaciones FHIR custom disponibles
- **Configuracion de recursos**: como se usa cada recurso FHIR localmente
- **Reglas de validacion**: notas sobre campos obligatorios en el contexto local

## Pack incluido: Argentina (`ar`)

SaludAI incluye el pack de Argentina como default con datos reales de
AR.FHIR.CORE / openRSD:

```python
from saludai_core.locales import load_locale_pack

pack = load_locale_pack("ar")  # Argentina (default)
print(pack.code)       # "ar"
print(pack.language)   # "es"
print(pack.name)       # "Argentina"

# FHIR awareness
print(len(pack.fhir_profiles))       # 6 profiles (Patient, Practitioner, ...)
print(len(pack.extensions))          # 7 extensions (Etnia, NOMIVAC, ...)
print(len(pack.identifier_systems))  # 3 (DNI, REFEPS, REFES)
print(len(pack.resource_configs))    # 8 resource types configurados
```

El system prompt del agente incluye automaticamente una seccion de "FHIR
awareness" generada desde esta metadata, para que el LLM conozca los perfiles,
extensiones e identificadores locales.

## Crear un nuevo Locale Pack

### 1. Estructura de archivos

```
saludai_core/locales/
  tu_pais/
    __init__.py          # re-export TU_LOCALE_PACK
    _pack.py             # definicion del pack
    _prompt.py           # system prompt localizado (base)
    snomed_local.csv     # datos de terminologia
    cie10_local.csv
```

### 2. CSVs de terminologia

Formato esperado (mismo que AR):

```csv
code,display,display_en,aliases
44054006,Diabetes mellitus tipo 2,Type 2 diabetes mellitus,diabetes tipo 2|DBT2
```

- `code`: codigo del sistema (SNOMED CT, CIE-10, LOINC)
- `display`: nombre en el idioma local (nombre primario)
- `display_en`: nombre en ingles
- `aliases`: aliases separados por `|` (para fuzzy matching)

### 3. Definir el pack

```python
# _pack.py
from saludai_core.locales._prompt_builder import build_fhir_awareness_section
from saludai_core.locales._types import (
    ExtensionDef,
    FHIRProfileDef,
    IdentifierSystemDef,
    LocalePack,
    LocaleResourceConfig,
    TerminologySystemDef,
)
from saludai_core.locales.tu_pais._prompt import SYSTEM_PROMPT_BR

SNOMED_CT_BR = TerminologySystemDef(
    key="snomed_ct",
    system_uri="http://snomed.info/sct",
    csv_filename="snomed_br.csv",
    display_name="SNOMED CT edicao brasileira",
    data_package="saludai_core.locales.br",
)

# Definir extensions, profiles, identifiers, resource configs...

_EXT_CPF = ExtensionDef(
    url="http://example.br/cpf",
    name="CPF",
    description="Cadastro de Pessoas Fisicas",
    value_type="Identifier",
    context="Patient",
)

_PATIENT_BR = FHIRProfileDef(
    resource_type="Patient",
    profile_url="http://example.br/Patient-br",
    name="Paciente BR",
    description="Perfil brasileiro com CPF",
    mandatory_extensions=(_EXT_CPF,),
)

def _build_br_pack() -> LocalePack:
    pack = LocalePack(
        code="br",
        name="Brasil",
        language="pt",
        terminology_systems=(SNOMED_CT_BR,),
        system_prompt="",  # placeholder
        tool_descriptions={...},
        tool_system_enum=("snomed_ct",),
        fhir_profiles=(_PATIENT_BR,),
        extensions=(_EXT_CPF,),
        identifier_systems=(...),
        resource_configs=(...),
    )
    awareness = build_fhir_awareness_section(pack)
    full_prompt = SYSTEM_PROMPT_BR + awareness
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
        identifier_systems=pack.identifier_systems,
        resource_configs=pack.resource_configs,
    )

BR_LOCALE_PACK = _build_br_pack()
```

### 4. Registrar en la factory

Actualmente, los packs se registran manualmente en `saludai_core/locales/__init__.py`. En el futuro, se podran descubrir via entry points de Python.

### 5. Usar en el agente

```bash
export SALUDAI_LOCALE=br
```

O programaticamente:

```python
from saludai_core.locales import load_locale_pack
from saludai_core.terminology import TerminologyResolver
from saludai_agent.loop import AgentLoop

pack = load_locale_pack("br")
resolver = TerminologyResolver(locale_pack=pack)
loop = AgentLoop(llm=llm, fhir_client=client, locale_pack=pack)
```

## Referencia de tipos

### `TerminologySystemDef`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `key` | `str` | Identificador corto (ej: `"snomed_ct"`) |
| `system_uri` | `str` | URI del sistema FHIR (ej: `"http://snomed.info/sct"`) |
| `csv_filename` | `str` | Nombre del CSV con conceptos |
| `display_name` | `str` | Nombre legible del sistema |
| `data_package` | `str` | Paquete Python donde buscar el CSV |

### `FHIRProfileDef`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `resource_type` | `str` | Tipo base FHIR (ej: `"Patient"`) |
| `profile_url` | `str` | URL canonica del StructureDefinition |
| `name` | `str` | Nombre legible del perfil |
| `description` | `str` | Que agrega o restringe este perfil |
| `mandatory_extensions` | `tuple[ExtensionDef, ...]` | Extensiones requeridas |

### `ExtensionDef`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `url` | `str` | URL canonica de la extension |
| `name` | `str` | Nombre corto |
| `description` | `str` | Que representa |
| `value_type` | `str` | Tipo FHIR del valor (ej: `"CodeableConcept"`) |
| `context` | `str` | Donde aplica (ej: `"Patient"`) |

### `IdentifierSystemDef`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `system_uri` | `str` | URI del sistema de identificacion |
| `name` | `str` | Nombre corto (ej: `"DNI"`) |
| `description` | `str` | Que identifica |
| `resource_types` | `tuple[str, ...]` | Recursos que lo usan |

### `CustomOperationDef`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `name` | `str` | Nombre con `$` (ej: `"$summary"`) |
| `resource_type` | `str \| None` | Recurso scope o `None` (server-level) |
| `description` | `str` | Que hace la operacion |

### `CustomSearchParamDef`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `name` | `str` | Nombre del parametro de busqueda |
| `resource_type` | `str` | Recurso al que aplica |
| `description` | `str` | Que busca |
| `expression` | `str` | FHIRPath expression |

### `LocaleResourceConfig`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `resource_type` | `str` | Tipo FHIR |
| `usage_note` | `str` | Como se usa localmente |
| `common_search_params` | `tuple[str, ...]` | Parametros de busqueda comunes |

### `LocalePack`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `code` | `str` | Codigo ISO del locale (ej: `"ar"`, `"br"`) |
| `name` | `str` | Nombre del pais/region |
| `language` | `str` | Codigo ISO 639-1 del idioma |
| `terminology_systems` | `tuple[TerminologySystemDef, ...]` | Sistemas de terminologia |
| `system_prompt` | `str` | Prompt completo del agente (base + awareness) |
| `tool_descriptions` | `dict[str, str]` | Descripciones de tools para el LLM |
| `tool_system_enum` | `tuple[str, ...]` | Valores validos del enum `system` |
| `fhir_profiles` | `tuple[FHIRProfileDef, ...]` | Perfiles FHIR locales |
| `extensions` | `tuple[ExtensionDef, ...]` | Extensiones FHIR locales |
| `custom_operations` | `tuple[CustomOperationDef, ...]` | Operaciones custom |
| `custom_search_params` | `tuple[CustomSearchParamDef, ...]` | SearchParameters custom |
| `identifier_systems` | `tuple[IdentifierSystemDef, ...]` | Sistemas de identificacion |
| `resource_configs` | `tuple[LocaleResourceConfig, ...]` | Config por recurso |
| `validation_notes` | `str` | Notas de validacion (texto libre) |
