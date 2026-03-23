"""Smoke test for saludai-agent package."""

from saludai_agent import __version__


def test_version() -> None:
    """Package version is defined and follows semver."""
    assert __version__ == "0.1.0"
