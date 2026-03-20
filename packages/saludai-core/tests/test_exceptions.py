"""Tests for the SaludAI exception hierarchy."""

from saludai_core.exceptions import (
    FHIRAuthenticationError,
    FHIRConnectionError,
    FHIRError,
    FHIRResourceNotFoundError,
    FHIRValidationError,
    SaludAIError,
)


def test_hierarchy_saludai_error_is_exception() -> None:
    """SaludAIError inherits from Exception."""
    assert issubclass(SaludAIError, Exception)


def test_hierarchy_fhir_error_inherits_saludai() -> None:
    """FHIRError inherits from SaludAIError."""
    assert issubclass(FHIRError, SaludAIError)


def test_hierarchy_fhir_subtypes() -> None:
    """All FHIR-specific errors inherit from FHIRError."""
    for exc_class in (
        FHIRConnectionError,
        FHIRResourceNotFoundError,
        FHIRAuthenticationError,
        FHIRValidationError,
    ):
        assert issubclass(exc_class, FHIRError), f"{exc_class.__name__} must inherit FHIRError"
        assert issubclass(exc_class, SaludAIError)


def test_message_preserved() -> None:
    """Error messages are accessible via str()."""
    msg = "something went wrong"
    err = FHIRConnectionError(msg)
    assert str(err) == msg


def test_catch_by_base_class() -> None:
    """All FHIR exceptions can be caught with 'except SaludAIError'."""
    try:
        raise FHIRResourceNotFoundError("Patient/123 not found")
    except SaludAIError as exc:
        assert "Patient/123" in str(exc)
