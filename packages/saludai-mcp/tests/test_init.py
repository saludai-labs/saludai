"""Smoke test for saludai-mcp package."""

from saludai_mcp import __version__


def test_version() -> None:
    """Package version is defined and follows semver."""
    assert __version__ == "0.1.0"
