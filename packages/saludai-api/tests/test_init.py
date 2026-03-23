"""Smoke test for saludai-api package."""

from saludai_api import __version__


def test_version() -> None:
    """Package version is defined and follows semver."""
    assert __version__ == "0.1.0"
