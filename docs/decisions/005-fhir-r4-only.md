# ADR-005: FHIR R4 Only

**Estado:** Aceptada
**Fecha:** 2026-03-03
**Autor:** Fede

## Contexto

HL7 FHIR tiene múltiples versiones publicadas:
- **DSTU2** (v1.0, 2015): Primera versión ampliamente implementada
- **STU3** (v3.0, 2017): Mejoras significativas, aún en uso
- **R4** (v4.0, 2019): Primera versión "normativa" — retrocompatibilidad garantizada
- **R5** (v5.0, 2023): Última versión, adopción incipiente
- **R6** (en desarrollo): Borrador

SaludAI necesita interactuar con servidores FHIR en el ecosistema de salud pública de Argentina y Latinoamérica. Debemos decidir qué versiones de FHIR soportar.

## Decisión

Soportar **exclusivamente FHIR R4** (v4.0.1). No se implementará soporte para DSTU2, STU3, R5, ni R6.

Esto aplica a:
- El FHIR client (`saludai-core`)
- Los modelos de datos y validaciones
- Las queries generadas por el agent
- El servidor HAPI FHIR de desarrollo
- Los datos sintéticos de seed

## Consecuencias

### Positivas
- **Simplicidad:** Un solo conjunto de resource schemas, search parameters, y behaviors
- **Ecosistema argentino:** openRSD (perfiles nacionales de Argentina) usa FHIR R4
- **HAPI FHIR:** El servidor de referencia tiene su mejor soporte en R4
- **Librerías Python:** `fhir.resources` tiene soporte completo y estable para R4
- **Estabilidad:** R4 es normativa — los resources no van a cambiar de forma breaking
- **Benchmark reproducible:** Un solo target simplifica la evaluación del agente

### Negativas
- **Sin soporte R5:** Algunas features nuevas de R5 (SubscriptionTopic, etc.) no están disponibles
- **Legacy excluido:** Servidores que solo hablan DSTU2/STU3 no son compatibles
- **Migración futura:** Si LATAM adopta R5 masivamente, requerirá trabajo de migración

### Riesgos
- Si un sistema de salud importante requiere R5, no podemos conectarnos sin trabajo adicional
- Mitigación: La abstracción `FHIRClient` puede extenderse para soportar múltiples versiones en el futuro; R4→R5 tiene alta compatibilidad en resources comunes (Patient, Condition, Observation)

## Alternativas consideradas

### Opción A: Multi-versión (R4 + R5)
- Pros: Mayor compatibilidad, futuro-proof
- Contras: Doble mantenimiento de schemas, search params, y validaciones; complejidad significativa en el agent loop para manejar diferencias entre versiones

### Opción B: R5 only
- Pros: Versión más nueva, mejores features
- Contras: Adopción mínima en LATAM, openRSD no tiene perfiles R5, HAPI FHIR R5 es menos probado

### Opción C: DSTU2 + R4 (máxima compatibilidad legacy)
- Pros: Soporta servidores legacy
- Contras: DSTU2 es fundamentalmente diferente en estructura; mantener dos modelos de datos es inviable para un equipo pequeño

## Referencias

- [HL7 FHIR R4 spec](https://hl7.org/fhir/R4/)
- [openRSD (Argentina)](https://simplifier.net/openrsd) — perfiles nacionales FHIR R4
- [HAPI FHIR server](https://hapifhir.io/) — servidor de referencia
- `packages/saludai-core/src/saludai_core/fhir_client.py` — client implementado para R4
- `data/seed/generate_seed_data.py` — datos sintéticos en formato R4
