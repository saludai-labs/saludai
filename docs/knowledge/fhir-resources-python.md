# fhir.resources — Python FHIR Models (v8+, Pydantic v2)

Documentación práctica de la librería `fhir.resources` para parsear y trabajar con recursos FHIR R4 en Python.

## Versión utilizada

- `fhir.resources>=8` (actualmente 8.2.0)
- Basada en Pydantic v2
- Compatible con FHIR R4 por defecto (no requiere sub-módulo especial como `fhir.resources.r4b`)

## API clave

### Parsear recursos

```python
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle

# Desde dict (respuesta JSON de FHIR server)
patient = Patient.model_validate(json_dict)

# Desde string JSON
patient = Patient.model_validate_json(json_string)

# Sin validación (rápido, inseguro)
patient = Patient.model_construct(**data)
```

### Obtener resource type

```python
# ✅ Correcto — es un MÉTODO, no un atributo
patient.get_resource_type()  # → "Patient"

# ❌ Incorrecto — NO existe como atributo
patient.resource_type   # → AttributeError
patient.resourceType    # → AttributeError
```

### Serializar

```python
patient.model_dump()       # → dict
patient.model_dump_json()  # → JSON string
```

### Import dinámico por nombre

```python
import importlib

def get_resource_class(resource_type: str):
    module = importlib.import_module(f"fhir.resources.{resource_type.lower()}")
    return getattr(module, resource_type)

# Uso
PatientClass = get_resource_class("Patient")
patient = PatientClass.model_validate(data)
```

### Imports comunes

```python
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.capabilitystatement import CapabilityStatement
from fhir.resources.medicationrequest import MedicationRequest
```

## Bundles

```python
bundle = Bundle.model_validate(search_response)

# Acceder a entries
if bundle.entry:
    for entry in bundle.entry:
        resource = entry.resource  # ya tipado como el recurso correcto
        resource.get_resource_type()  # "Patient", "Condition", etc.

# NOTA: bundle.total puede ser None (FHIR spec no lo obliga)
# Verificar bundle.entry en vez de confiar en bundle.total
```

## CapabilityStatement

```python
cap = CapabilityStatement.model_validate(metadata_response)
cap.fhirVersion  # "4.0.1" para HAPI FHIR R4
```

## Gotchas

1. **`get_resource_type()` es método, no atributo** — el error más común
2. **`bundle.total` puede ser `None`** — HAPI no siempre lo incluye en searchset
3. **`bundle.entry` es `None` (no lista vacía)** cuando no hay resultados — verificar con `bundle.entry is None or len(bundle.entry) == 0`
4. **fhir.resources v8+ migró de Pydantic v1 a v2** — usar `model_validate()` en vez de `parse_obj()`, `model_dump()` en vez de `dict()`

## Fuentes

- [PyPI: fhir.resources](https://pypi.org/project/fhir.resources/)
- [GitHub: nazrulworld/fhir.resources](https://github.com/nazrulworld/fhir.resources)
