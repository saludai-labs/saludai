# HAPI FHIR R4 — Docker Setup

> Investigación y configuración para desarrollo local con Docker.

## Imagen Docker

- **Imagen oficial:** `hapiproject/hapi:latest`
- **Fuente:** https://hub.docker.com/r/hapiproject/hapi
- **GitHub:** https://github.com/hapifhir/hapi-fhir-jpaserver-starter
- **Base:** Spring Boot sobre JVM — tarda 30-60s en arrancar

## Configuración vía Environment Variables

HAPI FHIR acepta config vía env vars con el prefijo `hapi.fhir.*`:

```yaml
environment:
  hapi.fhir.fhir_version: R4
  hapi.fhir.allow_multiple_delete: "true"
```

Variables útiles:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `hapi.fhir.fhir_version` | R4 | Versión de FHIR |
| `hapi.fhir.allow_multiple_delete` | false | Permite DELETE en batch |
| `hapi.fhir.server_address` | auto | URL pública del servidor |
| `hapi.fhir.cors.allowed_origin` | `*` | CORS origins |

## Storage

- **Default:** H2 en memoria (datos efímeros, se pierden al reiniciar)
- **Producción:** PostgreSQL vía `spring.datasource.*` env vars
- **Nuestra elección:** H2 en memoria — datos se re-seedean al levantar, más simple

## Healthcheck

El endpoint `/fhir/metadata` retorna el CapabilityStatement y es el check canónico.

**IMPORTANTE:** La imagen `hapiproject/hapi:latest` es **distroless** — no tiene shell (`/bin/sh`), ni `curl`, ni `wget`. Esto hace imposible usar Docker healthchecks nativos (`CMD-SHELL` o `CMD` con curl/wget).

### Estrategia: polling desde el sidecar

En vez de Docker healthcheck, el container seed (Alpine con curl) hace el polling:

```sh
for i in $(seq 1 60); do
  if curl -sf http://hapi-fhir:8080/fhir/metadata > /dev/null 2>&1; then
    break
  fi
  sleep 5
done
```

- HAPI tarda ~30s en arrancar, el polling da hasta 5 minutos de margen
- El sidecar tiene curl (Alpine) así que puede hacer el check

## Seeding de datos

### Estrategia: Bundle transaccional + sidecar container

1. Un script Python genera un **FHIR Transaction Bundle** (`seed_bundle.json`)
2. Un container sidecar (`fhir-seed`) espera a que HAPI esté healthy
3. El sidecar POSTea el bundle a `POST /fhir` con `Content-Type: application/fhir+json`
4. HAPI procesa todas las entradas atómicamente
5. El sidecar verifica con `Patient?_summary=count` y sale

### Transaction Bundle format

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:<uuid>",
      "resource": { "resourceType": "Patient", ... },
      "request": {
        "method": "POST",
        "url": "Patient"
      }
    }
  ]
}
```

- `urn:uuid:` permite referencias internas entre recursos del mismo bundle
- HAPI resuelve las refs automáticamente al persistir

## Tips y problemas comunes

- **Puerto 8080** es el default — no mover para evitar confusión con docs
- **`_summary=count`** retorna solo el total, útil para verificación rápida
- **Imagen distroless:** No hay shell, curl, wget, ni ls. Es JVM puro — healthcheck desde el sidecar
- **Logs:** HAPI loguea mucho al arrancar — es normal, no es un error
- **Memory:** Default heap es ~1GB, suficiente para desarrollo con <1000 recursos

## Referencias

- [HAPI FHIR JPA Server Starter](https://github.com/hapifhir/hapi-fhir-jpaserver-starter)
- [HAPI Docker Hub](https://hub.docker.com/r/hapiproject/hapi)
- [FHIR Transaction Bundle spec](https://www.hl7.org/fhir/http.html#transaction)
