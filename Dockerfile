FROM python:3.12-slim AS base

LABEL maintainer="SaludAI Labs"
LABEL org.opencontainers.image.source="https://github.com/saludai-labs/saludai"
LABEL org.opencontainers.image.description="SaludAI — The most precise FHIR agent for Latin America"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install UV for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace definition and lockfile first (cache-friendly)
COPY pyproject.toml uv.lock ./
COPY packages/saludai-core/pyproject.toml packages/saludai-core/pyproject.toml
COPY packages/saludai-agent/pyproject.toml packages/saludai-agent/pyproject.toml
COPY packages/saludai-mcp/pyproject.toml packages/saludai-mcp/pyproject.toml

# Copy source code
COPY src/ src/
COPY packages/saludai-core/src/ packages/saludai-core/src/
COPY packages/saludai-agent/src/ packages/saludai-agent/src/
COPY packages/saludai-mcp/src/ packages/saludai-mcp/src/

# Install all packages (excluding dev dependencies and saludai-api)
RUN uv sync --no-dev --no-install-package saludai-api

ENTRYPOINT ["uv", "run", "saludai"]
CMD ["mcp"]
