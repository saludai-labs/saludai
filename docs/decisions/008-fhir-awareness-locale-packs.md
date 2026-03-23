# ADR-008: FHIR Awareness en Locale Packs

**Estado:** Aceptada
**Autor:** SaludAI

## Contexto

Los locale packs (ADR-007) cubren terminologia y localizacion de UI (prompts,
descripciones), pero no contemplan las customizaciones FHIR estructurales que
cada pais/implementacion define: profiles, extensions, operaciones custom,
parametros de busqueda, sistemas de identificacion, y reglas de validacion.

FHIR es un estandar extensible por diseno. Cada implementacion nacional (como
openRSD/AR.FHIR.CORE en Argentina) define profiles que agregan campos
obligatorios (ej: DNI), extensiones custom (ej: etnia, esquema NOMIVAC), y
sistemas de identificacion propios (RENAPER, REFEPS, REFES).

Para que el agente sea verdaderamente adaptable a diferentes paises, necesita
*conocer* estas customizaciones locales.

## Decision

Implementar FHIR awareness en dos niveles:

### Level 1 - Awareness (implementado)

Extender `LocalePack` con metadata declarativa sobre la implementacion FHIR
local. El agente recibe esta metadata como parte del system prompt (generada
dinamicamente por `build_fhir_awareness_section`). El agente *sabe* que existen
profiles, extensions, identificadores, etc. y puede mencionarlos, pero no
valida contra ellos.

Nuevos tipos:
- `FHIRProfileDef` - perfiles con extensiones obligatorias
- `ExtensionDef` - extensiones FHIR con URL, tipo, contexto
- `IdentifierSystemDef` - sistemas de identificacion (DNI, CUIL, etc.)
- `CustomOperationDef` - operaciones FHIR custom ($summary, etc.)
- `CustomSearchParamDef` - parametros de busqueda custom
- `LocaleResourceConfig` - como se usa cada recurso localmente

### Level 2 - Ejecucion (planificado)

El agente valida responses contra profiles, usa operaciones custom, y parsea
extensiones inteligentemente. Planificado para Sprint 5 o inicio de Etapa 2.

## Consecuencias

### Positivas
- El agente conoce el contexto FHIR local sin hardcodear en el prompt
- Agregar un nuevo pais es declarativo: definir metadata, el prompt se genera solo
- Backward compatible: todos los campos nuevos tienen defaults vacios
- Diferenciador claro: "adaptable a cualquier implementacion FHIR nacional"

### Negativas
- El system prompt crece (~50 lineas extra para AR) — mas tokens por request
- La metadata puede desactualizarse si la IG local cambia

### Riesgos
- Level 2 requiere acceso a servidores FHIR reales con profiles/extensions
  para testear validacion

## Alternativas consideradas

### Opcion A: Hardcodear en el prompt
- Pros: Simple, rapido
- Contras: No escala, no es reutilizable, no permite generar prompt por pais

### Opcion B: Cargar StructureDefinitions desde el servidor FHIR
- Pros: Siempre actualizado
- Contras: Requiere conexion, lento, complejo de parsear, no disponible offline

### Opcion C: Metadata declarativa en locale pack (elegida)
- Pros: Offline, versionable, simple, extensible
- Contras: Puede desactualizarse

## Referencias

- AR.FHIR.CORE IG: https://guias.hl7.org.ar/site/index.html
- Simplifier SaludDigital.ar: https://simplifier.net/SaludDigital.ar
- openRSD GitHub: https://github.com/SALUD-AR/Open-RSD
- ADR-007: Locale Packs
