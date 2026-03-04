# SaludAI — Knowledge Base

Documentación de hallazgos de investigación técnica. A diferencia de los ADRs (`docs/decisions/`), estos documentos **no son decisiones** sino conocimiento técnico acumulado.

## Convenciones

- **Un archivo por tema** — no mezclar temas distintos.
- **Actualizar, no duplicar** — si ya existe un doc sobre el tema, actualizarlo.
- **Fuentes siempre** — incluir links a documentación oficial, issues, etc.
- **Práctico, no teórico** — comandos, configuraciones, tips que realmente usamos.

## Contenido

| Archivo | Tema |
|---------|------|
| `hapi-fhir-docker.md` | HAPI FHIR R4: imagen Docker, configuración, healthcheck, seeding |
| `langfuse-setup.md` | Langfuse: Cloud vs self-hosted, env vars, integración |
| `fhir-resources-python.md` | fhir.resources v8+: API, parsing, gotchas, imports dinámicos |
| [`../experiments/EXPERIMENTS.md`](../experiments/EXPERIMENTS.md) | Estrategia experimental: benchmarks, ablation studies, matriz de modelos |
