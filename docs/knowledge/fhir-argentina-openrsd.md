# FHIR Argentina — AR.FHIR.CORE / openRSD

> Investigacion realizada 2026-03-05. Fuentes: HL7 Argentina, Simplifier,
> MSAL, GitHub SALUD-AR.

## Implementation Guide

- **Nombre:** AR.FHIR.CORE (paquete `ar.fhir.core#0.5.0`)
- **Base FHIR:** R4 (4.0.1)
- **Publicado por:** DNSIS (Ministerio de Salud) + HL7 Argentina
- **URL canonica base:** `http://fhir.msal.gov.ar/core/StructureDefinition/`

## URLs clave

| Recurso | URL |
|---------|-----|
| IG (HL7 Argentina) | https://guias.hl7.org.ar/site/index.html |
| IG (MSAL bus) | https://bus.msal.gob.ar/fhir/ar/core/site/ |
| HAPI FHIR server | https://fhir.msal.gob.ar/ |
| Simplifier project | https://simplifier.net/SaludDigital.ar |
| GitHub IPS | https://github.com/SALUD-AR/IPS-Argentina |
| GitHub Open-RSD | https://github.com/SALUD-AR/Open-RSD |
| Practitioner REFEPS guide | https://simplifier.net/guide/practitionerrefeps/ |
| NOMIVAC WS API | https://apisalud.msal.gob.ar/nomivacAplicacion/v1/aplicaciones/alta/ |
| SISA docs | https://sisa.msal.gov.ar/sisadoc/ |
| SNOMED CT AR | https://www.argentina.gob.ar/salud/snomed |
| Estandares digitales | https://www.argentina.gob.ar/salud/digital/estandares |

## Profiles

| Profile | Resource | URL canonica |
|---------|----------|-------------|
| Patient-ar-core | Patient | `http://fhir.msal.gov.ar/core/StructureDefinition/Patient-ar-core` |
| Practitioner-ar-core | Practitioner | `http://fhir.msal.gov.ar/core/StructureDefinition/Practitioner-ar-core` |
| Organization-ar-core | Organization | `http://fhir.msal.gov.ar/core/StructureDefinition/Organization-ar-core` |
| Location-ar-core | Location | `http://fhir.msal.gov.ar/core/StructureDefinition/Location-ar-core` |
| Immunization-ar-core | Immunization | `http://fhir.msal.gov.ar/core/StructureDefinition/Immunization-ar-core` |
| Consent-ar-core | Consent | (Consentimiento para Obtencion IPS) |
| DocumentReference-ar-core | DocumentReference | (confirmado via IG) |
| Composition-ar-ips-core | Composition | `http://fhir.msal.gov.ar/StructureDefinition/Composition_ar_ips` |
| Bundle-ar-ips-core | Bundle | (IPS bundle profile) |

### Profiles del Federador (Simplifier/SaludDigital.ar)

| Profile | URL canonica | Notas |
|---------|-------------|-------|
| FederadorPatientR4 | `http://fhir.msal.gov.ar/StructureDefinition/federadorPatientR4` | Draft, FHIR R4, deriva de ArgPatient |
| FederadorPatient (retired) | `https://federador.msal.gob.ar/StructureDefinition/Patient` | STU3, retirado |
| NOMIVAC Immunization | (en Simplifier) | Para reporte de vacunacion |
| PractitionerREFEPS | (guia separada) | Registro de profesionales |

### IPS Argentina

`Composition-ar-ips-core` deriva de `http://hl7.org/fhir/uv/ips/StructureDefinition/composition-uv-ips`
y agrega seccion obligatoria `sectionImmunizations`.

## Extensions

| Extension | URL canonica | Tipo valor | Contexto | Descripcion |
|-----------|-------------|------------|----------|-------------|
| Etnia | `http://fhir.msal.gov.ar/StructureDefinition/Etnia` | CodeableConcept | Patient | Grupo etnico. Bound a SNOMED CT AR (`http://snomed.info/sct/11000221109?fhir_vs=isa/372148003`) |
| NomivacEsquema | `http://fhir.msal.gov.ar/StructureDefinition/NomivacEsquema` | Coding | Immunization.protocolApplied.series | Codigo de esquema de vacunacion NOMIVAC. Required binding a `http://fhir.msal.gov.ar/ValueSet/NOMIVAC-esquema-code` |
| MatriculaHabilitada | `http://fhir.msal.gob.ar/StructureDefinition/MatriculaHabilitada` | boolean | Practitioner.qualification | Si la matricula del profesional esta activa |
| FechaModificacionMatricula | `http://fhir.msal.gob.ar/StructureDefinition/FechaModificacionMatricula` | date | Practitioner.qualification.period | Fecha de modificacion de la matricula |
| fathers-family | `http://hl7.org/fhir/StructureDefinition/humanname-fathers-family` | string | HumanName.family | Extension estandar FHIR, usada en perfiles AR |
| mothers-family | `http://hl7.org/fhir/StructureDefinition/humanname-mothers-family` | string | HumanName.family | Extension estandar FHIR, usada en perfiles AR |
| genderIdentity | `http://hl7.org/fhir/StructureDefinition/patient-genderIdentity` | CodeableConcept | Patient | Extension estandar FHIR, usada en FederadorPatientR4 |
| birthPlace | `http://hl7.org/fhir/StructureDefinition/patient-birthPlace` | Address | Patient | Extension estandar FHIR, usada en FederadorPatientR4 |

### Extensions retiradas

| Extension | URL | Notas |
|-----------|-----|-------|
| primer_apellido | `https://federador.msal.gob.ar/primer_apellido` | Reemplazada por fathers-family |
| SegundoApellido | `https://federador.msal.gob.ar/StructureDefinition/Patient/SegundoApellido` | Reemplazada por mothers-family |

## Sistemas de identificacion

| System URI | Nombre | Tipo | Descripcion |
|------------|--------|------|-------------|
| `http://www.renaper.gob.ar/dni` | DNI | NI (official) | Documento Nacional de Identidad |
| `https://sisa.msal.gov.ar/REFEPS` | REFEPS | usual | Registro Federal de Profesionales de Salud |
| `http://argentina.gob.ar/salud/refes` | REFES | - | Registro Federal de Establecimientos de Salud (codigo 14 digitos) |
| `http://argentina.gob.ar/salud/bus-interoperabilidad/dominio` | Bus dominio | - | ID de dominio del Bus de Interoperabilidad |

### Requisitos del FederadorPatientR4

- **Exactamente 2 identifiers** requeridos (`min:2, max:2`)
- Slice 1: `dni` — system `http://www.renaper.gob.ar/dni`, type `NI`, use `official` (1..1)
- Slice 2: `idDominio` — ID de paciente especifico del dominio federador (1..1)

## Sistemas de terminologia

| Sistema | URI | Descripcion |
|---------|-----|-------------|
| SNOMED CT (edicion AR) | `http://snomed.info/sct` (con `version` o `11000221109`) | Extension argentina. URI vacunas SCT: `https://snomed.info/sct/11000221109/id/228100022110` |
| CIE-10 | `http://hl7.org/fhir/sid/icd-10` | Adaptacion argentina |
| LOINC | `http://loinc.org` | Observaciones de laboratorio, tipos de documentos |
| NOMIVAC-esquema | `http://fhir.msal.gov.ar/CodeSystem/NOMIVAC-esquema` | 145 codigos de esquemas de vacunacion |
| NOMIVAC-condicion | `http://saluddigital.ar/valueSet/NOMIVAC-condicion-code` | Codigos de condicion de vacunacion |
| ProfesionesREFEPS | (CodeSystem en bus.msal.gob.ar) | Codigos de profesiones de salud de REFEPS |
| entidadesCertificantesREFEPS | (ValueSet) | Entidades certificantes de matriculas profesionales |

## Operaciones custom

| Operacion | Tipo | Descripcion |
|-----------|------|-------------|
| federadorMatch | OperationDefinition | Patient matching para federacion (retirado en Simplifier, pero operacionalmente usado) |
| $summary | Patient | Genera resumen IPS (International Patient Summary) |

## Recursos usados en salud publica argentina

Del IPS Argentina y AR.FHIR.CORE IG:

- **Patient** — Datos demograficos, DNI, cobertura
- **Practitioner** — Profesionales de salud (REFEPS)
- **Organization** — Establecimientos de salud (REFES)
- **Location** — Ubicaciones fisicas
- **Condition** — Diagnosticos (SNOMED CT AR)
- **Immunization** — Registros de vacunacion (NOMIVAC)
- **Medication** — Formulaciones de medicamentos
- **MedicationStatement** — Tratamientos activos
- **AllergyIntolerance** — Alergias
- **Observation** — Resultados de laboratorio, embarazo
- **Composition** — Documento IPS
- **Bundle** — Bundle IPS
- **Consent** — Consentimiento de acceso IPS
- **DocumentReference** — Referencias a documentos clinicos
- **Device** — Identificacion de sistema EHR
- **DiagnosticReport** — Reportes de laboratorio/imagenes

## Reglas de validacion (FederadorPatientR4)

### Campos obligatorios

- `identifier`: exactamente 2 (DNI + domain ID)
- `active`: requerido (1..1)
- `name`: requerido (1..1), con `family` (1..1) y `given` (1..*)
- `name.text`: requerido (1..1)
- `gender`: requerido (1..1)
- `birthDate`: requerido (1..1)

### Campos excluidos (max:0 en perfil Federador antiguo)

- address, maritalStatus, photo, contact
- telecom: limitado a 1

## Notas

- La IG se publica intermitentemente en bus.msal.gob.ar
- Simplifier tiene la version mas actualizada de los profiles
- El servidor HAPI FHIR de MSAL esta en https://fhir.msal.gob.ar/
- La edicion argentina de SNOMED CT tiene OID `11000221109`
- openRSD es el nombre del proyecto open source, AR.FHIR.CORE es la IG formal

## Fuentes primarias (para re-investigacion)

> Si algo cambia en el futuro, estas son las fuentes autoritativas para
> verificar y actualizar la metadata del locale pack AR.

### Profiles y Extensions (StructureDefinitions)

- **Simplifier — SaludDigital.ar** (fuente mas completa y actualizada):
  https://simplifier.net/SaludDigital.ar/~resources?category=Profile
  https://simplifier.net/SaludDigital.ar/~resources?category=Extension
- **FederadorPatientR4** (perfil Patient del Federador, detalle de slices e identifiers):
  https://simplifier.net/SaludDigital.ar/FederadorPatientR4
- **IG oficial HL7 Argentina** (puede estar desactualizada vs Simplifier):
  https://guias.hl7.org.ar/site/index.html
- **IG bus MSAL** (intermitente, a veces offline):
  https://bus.msal.gob.ar/fhir/ar/core/site/
- **GitHub IPS Argentina** (Composition IPS, Bundle IPS):
  https://github.com/SALUD-AR/IPS-Argentina
- **GitHub Open-RSD** (proyecto open source original):
  https://github.com/SALUD-AR/Open-RSD

### Terminologia

- **SNOMED CT Argentina** (pagina oficial, edicion AR):
  https://www.argentina.gob.ar/salud/snomed
- **SNOMED CT AR browser** (si existe, buscar en):
  https://browser.ihtsdotools.org/ (filtrar por extension argentina `11000221109`)
- **NOMIVAC CodeSystem** (145 esquemas de vacunacion):
  http://fhir.msal.gov.ar/CodeSystem/NOMIVAC-esquema
  https://sisa.msal.gov.ar/sisadoc/docs/050203/nomivac_ws_200.jsp

### Identificadores y registros

- **RENAPER** (DNI system URI `http://www.renaper.gob.ar/dni`):
  https://www.argentina.gob.ar/interior/renaper
- **REFEPS** (Registro Federal de Profesionales):
  https://sisa.msal.gov.ar/sisadoc/ (buscar seccion REFEPS)
  https://simplifier.net/guide/practitionerrefeps/
- **REFES** (Registro Federal de Establecimientos):
  https://sisa.msal.gov.ar/sisadoc/ (buscar seccion REFES)

### Servidor FHIR de referencia

- **HAPI FHIR MSAL** (servidor publico para pruebas):
  https://fhir.msal.gob.ar/
  Ejemplo: https://fhir.msal.gob.ar/fhir/Patient?_count=5
  Ejemplo: https://fhir.msal.gob.ar/fhir/metadata (CapabilityStatement)

### Estandares y normativa

- **Estandares de Salud Digital Argentina** (pagina oficial MSAL):
  https://www.argentina.gob.ar/salud/digital/estandares
- **HL7 Argentina** (capitulo local):
  https://www.hl7.org.ar/
- **Resolucion MSAL** sobre interoperabilidad:
  Buscar en https://www.argentina.gob.ar/salud/digital

### Estrategia de busqueda para actualizaciones

1. **Simplifier** es la fuente mas confiable — verificar profiles y extensions ahi primero
2. **GitHub SALUD-AR** para cambios en IPS y Open-RSD
3. **bus.msal.gob.ar** para la IG oficial (puede estar offline)
4. **sisa.msal.gov.ar/sisadoc** para documentacion de NOMIVAC, REFEPS, REFES
5. Buscar "AR.FHIR.CORE" o "guia implementacion FHIR Argentina" para nuevas versiones de la IG
