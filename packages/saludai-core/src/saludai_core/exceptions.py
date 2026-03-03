"""SaludAI exception hierarchy.

All exceptions raised by saludai-core inherit from ``SaludAIError`` so callers
can catch the whole family with a single ``except SaludAIError``.
"""

from __future__ import annotations


class SaludAIError(Exception):
    """Base exception for all SaludAI errors."""


class FHIRError(SaludAIError):
    """Base exception for FHIR-related errors."""


class FHIRConnectionError(FHIRError):
    """FHIR server is unreachable or returned a network-level error."""


class FHIRResourceNotFoundError(FHIRError):
    """Requested FHIR resource does not exist (HTTP 404)."""


class FHIRAuthenticationError(FHIRError):
    """FHIR server rejected credentials (HTTP 401/403)."""


class FHIRValidationError(FHIRError):
    """FHIR server returned an invalid or unexpected response."""
