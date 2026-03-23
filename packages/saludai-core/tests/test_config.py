"""Tests for FHIRConfig settings."""

import os

from saludai_core.config import FHIRConfig


def test_defaults() -> None:
    """FHIRConfig provides sensible defaults."""
    config = FHIRConfig()
    assert config.fhir_server_url == "http://localhost:8080/fhir"
    assert config.fhir_auth_type == "none"
    assert config.fhir_auth_token is None
    assert config.fhir_timeout == 30.0


def test_env_override(monkeypatch: object) -> None:
    """Settings can be overridden via SALUDAI_ env vars."""
    os.environ["SALUDAI_FHIR_SERVER_URL"] = "https://fhir.example.com/r4"
    os.environ["SALUDAI_FHIR_AUTH_TYPE"] = "bearer"
    os.environ["SALUDAI_FHIR_AUTH_TOKEN"] = "secret-token"
    os.environ["SALUDAI_FHIR_TIMEOUT"] = "60.0"
    try:
        config = FHIRConfig()
        assert config.fhir_server_url == "https://fhir.example.com/r4"
        assert config.fhir_auth_type == "bearer"
        assert config.fhir_auth_token == "secret-token"
        assert config.fhir_timeout == 60.0
    finally:
        del os.environ["SALUDAI_FHIR_SERVER_URL"]
        del os.environ["SALUDAI_FHIR_AUTH_TYPE"]
        del os.environ["SALUDAI_FHIR_AUTH_TOKEN"]
        del os.environ["SALUDAI_FHIR_TIMEOUT"]


def test_explicit_values() -> None:
    """Config accepts explicit keyword arguments."""
    config = FHIRConfig(
        fhir_server_url="https://custom.fhir/api",
        fhir_auth_type="bearer",
        fhir_auth_token="my-token",
        fhir_timeout=10.0,
    )
    assert config.fhir_server_url == "https://custom.fhir/api"
    assert config.fhir_auth_type == "bearer"
    assert config.fhir_auth_token == "my-token"
    assert config.fhir_timeout == 10.0
