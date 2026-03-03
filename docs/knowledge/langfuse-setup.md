# Langfuse — Setup y Configuración

> Investigación sobre opciones de deployment y configuración.

## Cloud vs Self-hosted

| Aspecto | Cloud (cloud.langfuse.com) | Self-hosted |
|---------|---------------------------|-------------|
| Setup | Crear cuenta, copiar keys | Docker Compose + PostgreSQL |
| Costo | Free tier generoso | Gratis pero más infra |
| Mantenimiento | Cero | Updates, backups, etc. |
| Containers | 0 | 2 (langfuse + postgres) |
| Latencia traces | ~100ms (remote) | ~1ms (local) |
| Datos sensibles | En sus servers (US/EU) | En tu máquina |

### Decisión: Cloud free tier para desarrollo

- **Razón principal:** Menos containers = docker-compose más simple y rápido
- **Free tier incluye:** 50k observaciones/mes, suficiente para desarrollo
- **Migración:** Si en producción necesitamos self-hosted, solo cambian env vars
- **ADR:** `docs/decisions/006-langfuse-cloud.md`

## Configuración (Cloud)

### Environment Variables

```bash
# En .env
SALUDAI_LANGFUSE_ENABLED=true
SALUDAI_LANGFUSE_HOST=https://cloud.langfuse.com

# Keys de Langfuse (se obtienen en Settings > API Keys del proyecto)
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-key-here
```

### Setup en cloud.langfuse.com

1. Crear cuenta en https://cloud.langfuse.com
2. Crear proyecto "SaludAI"
3. Ir a Settings > API Keys
4. Copiar Public Key y Secret Key a `.env`
5. Verificar: el SDK se conecta automáticamente al detectar las env vars

## Integración con Python SDK

```python
from langfuse import Langfuse

# Se configura automáticamente desde env vars
langfuse = Langfuse()

# Decorador para tracing
from langfuse.decorators import observe

@observe()
async def my_llm_call():
    ...
```

El SDK de Langfuse lee automáticamente:
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST` (default: `https://cloud.langfuse.com`)

## Self-hosted (referencia futura)

Si en el futuro necesitamos self-hosted (datos sensibles, producción):

```yaml
# Se agregarían estos services a docker-compose.yml:
langfuse:
  image: langfuse/langfuse:2
  ports: ["3000:3000"]
  environment:
    DATABASE_URL: postgresql://langfuse:langfuse@langfuse-db:5432/langfuse
    NEXTAUTH_SECRET: mysecret
    NEXTAUTH_URL: http://localhost:3000
  depends_on:
    langfuse-db:
      condition: service_healthy

langfuse-db:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: langfuse
    POSTGRES_PASSWORD: langfuse
    POSTGRES_DB: langfuse
  volumes:
    - langfuse-data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U langfuse"]
    interval: 5s
    timeout: 3s
    retries: 10
```

## Referencias

- [Langfuse Cloud](https://cloud.langfuse.com)
- [Langfuse Self-hosting docs](https://langfuse.com/docs/deployment/self-host)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)
- [Langfuse pricing](https://langfuse.com/pricing)
