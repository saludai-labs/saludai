# SaludAI — Lecciones Aprendidas

> Actualizar después de CADA corrección del usuario.
> Claude Code debe leer este archivo al inicio de cada sesión.
> Formato: fecha + patrón + regla para evitarlo.

---

## Reglas activas

_Ninguna todavía. Se irán agregando durante el desarrollo._

<!-- Ejemplo de formato:
### 2026-03-05: No usar requests, usar httpx
**Qué pasó:** Usé `requests` para el FHIR client.
**Por qué estuvo mal:** El proyecto usa httpx (async-first). requests bloquea el event loop.
**Regla:** Siempre usar `httpx.AsyncClient` para HTTP. Never import requests.
-->
