# Guía de Locale Packs

> Cómo crear un locale pack para extender SaludAI a tu país/región.

## ¿Qué es un Locale Pack?

Un locale pack contiene toda la configuración específica de un país o región:

- **Sistemas de terminología**: qué CSVs de SNOMED CT, CIE-10, LOINC u otros usar
- **System prompt**: el prompt completo del agente, localizado
- **Descripciones de tools**: texto que el LLM ve para cada herramienta
- **Enum de sistemas**: valores válidos para el parámetro `system` de `resolve_terminology`

## Pack incluido: Argentina (`ar`)

SaludAI incluye el pack de Argentina como default:

```python
from saludai_core.locales import load_locale_pack

pack = load_locale_pack("ar")  # Argentina (default)
print(pack.code)       # "ar"
print(pack.language)   # "es"
print(pack.name)       # "Argentina"
```

## Crear un nuevo Locale Pack

### 1. Estructura de archivos

```
saludai_core/locales/
  tu_pais/
    __init__.py          # re-export TU_LOCALE_PACK
    _pack.py             # definición del pack
    _prompt.py           # system prompt localizado
    snomed_local.csv     # datos de terminología
    cie10_local.csv
```

### 2. CSVs de terminología

Formato esperado (mismo que AR):

```csv
code,display,display_en,aliases
44054006,Diabetes mellitus tipo 2,Type 2 diabetes mellitus,diabetes tipo 2|DBT2
```

- `code`: código del sistema (SNOMED CT, CIE-10, LOINC)
- `display`: nombre en el idioma local (nombre primario)
- `display_en`: nombre en inglés
- `aliases`: aliases separados por `|` (para fuzzy matching)

### 3. Definir el pack

```python
# _pack.py
from saludai_core.locales._types import LocalePack, TerminologySystemDef
from saludai_core.locales.tu_pais._prompt import SYSTEM_PROMPT_BR

SNOMED_CT_BR = TerminologySystemDef(
    key="snomed_ct",
    system_uri="http://snomed.info/sct",
    csv_filename="snomed_br.csv",
    display_name="SNOMED CT edição brasileira",
    data_package="saludai_core.locales.br",
)

# ... definir CIE_10_BR, LOINC_BR, etc.

BR_LOCALE_PACK = LocalePack(
    code="br",
    name="Brasil",
    language="pt",
    terminology_systems=(SNOMED_CT_BR, ...),
    system_prompt=SYSTEM_PROMPT_BR,
    tool_descriptions={
        "resolve_terminology": "Resolve um termo clínico...",
        "search_fhir": "Executa uma busca no servidor FHIR R4...",
        "get_resource": "Lê um recurso FHIR individual...",
        "execute_code": "Executa código Python para processar dados...",
    },
    tool_system_enum=("snomed_ct", "cie_10", "loinc"),
)
```

### 4. Registrar en la factory

Actualmente, los packs se registran manualmente en `saludai_core/locales/__init__.py`. En el futuro, se podrán descubrir via entry points de Python.

### 5. Usar en el agente

```bash
export SALUDAI_LOCALE=br
```

O programáticamente:

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

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `key` | `str` | Identificador corto (ej: `"snomed_ct"`) |
| `system_uri` | `str` | URI del sistema FHIR (ej: `"http://snomed.info/sct"`) |
| `csv_filename` | `str` | Nombre del CSV con conceptos |
| `display_name` | `str` | Nombre legible del sistema |
| `data_package` | `str` | Paquete Python donde buscar el CSV |

### `LocalePack`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `code` | `str` | Código ISO del locale (ej: `"ar"`, `"br"`) |
| `name` | `str` | Nombre del país/región |
| `language` | `str` | Código ISO 639-1 del idioma |
| `terminology_systems` | `tuple[TerminologySystemDef, ...]` | Sistemas de terminología |
| `system_prompt` | `str` | Prompt del agente |
| `tool_descriptions` | `dict[str, str]` | Descripciones de tools para el LLM |
| `tool_system_enum` | `tuple[str, ...]` | Valores válidos del enum `system` |
