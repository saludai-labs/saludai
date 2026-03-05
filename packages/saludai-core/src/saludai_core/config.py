"""Configuration for SaludAI FHIR client.

Settings are loaded from environment variables with the ``SALUDAI_`` prefix.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class FHIRConfig(BaseSettings):
    """FHIR server connection settings.

    Attributes:
        fhir_server_url: Base URL of the FHIR R4 server.
        fhir_auth_type: Authentication method (``"none"`` or ``"bearer"``).
        fhir_auth_token: Bearer token when ``fhir_auth_type`` is ``"bearer"``.
        fhir_timeout: HTTP request timeout in seconds.
    """

    model_config = SettingsConfigDict(env_prefix="SALUDAI_")

    fhir_server_url: str = "http://localhost:8080/fhir"
    fhir_auth_type: Literal["none", "bearer"] = "none"
    fhir_auth_token: str | None = None
    fhir_timeout: float = 30.0
