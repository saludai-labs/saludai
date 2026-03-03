"""SaludAI Core — FHIR client, terminology resolver, and shared types."""

from __future__ import annotations

__version__ = "0.1.0"

from saludai_core.config import FHIRConfig
from saludai_core.exceptions import (
    FHIRAuthenticationError,
    FHIRConnectionError,
    FHIRError,
    FHIRResourceNotFoundError,
    FHIRValidationError,
    SaludAIError,
)
from saludai_core.fhir_client import FHIRClient

__all__ = [
    "FHIRAuthenticationError",
    "FHIRClient",
    "FHIRConfig",
    "FHIRConnectionError",
    "FHIRError",
    "FHIRResourceNotFoundError",
    "FHIRValidationError",
    "SaludAIError",
]
