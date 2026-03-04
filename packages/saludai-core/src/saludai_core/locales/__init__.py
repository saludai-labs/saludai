"""Locale pack registry and loader.

Use ``load_locale_pack(code)`` to obtain a ``LocalePack`` for a given locale.
Currently ships with ``"ar"`` (Argentina) as the default and only built-in
locale.  Future locales can be added as built-in packs or discovered via
``importlib.metadata.entry_points(group="saludai.locales")`` (backlog).
"""

from __future__ import annotations

from saludai_core.exceptions import LocaleNotFoundError
from saludai_core.locales._types import LocalePack, TerminologySystemDef

# ---------------------------------------------------------------------------
# Built-in locale registry (lazy — imported on first access)
# ---------------------------------------------------------------------------

_BUILTIN_LOCALES: frozenset[str] = frozenset({"ar"})


def load_locale_pack(code: str = "ar") -> LocalePack:
    """Load a locale pack by its code.

    Args:
        code: Locale code (e.g. ``"ar"``).  Defaults to ``"ar"``.

    Returns:
        The corresponding ``LocalePack``.

    Raises:
        LocaleNotFoundError: If no pack exists for the given code.
    """
    if code == "ar":
        from saludai_core.locales.ar import AR_LOCALE_PACK

        return AR_LOCALE_PACK

    # Future: entry_points discovery would go here
    raise LocaleNotFoundError(
        f"Locale pack {code!r} not found. Available locales: {sorted(_BUILTIN_LOCALES)}"
    )


def available_locales() -> list[str]:
    """Return codes of all available built-in locale packs."""
    return sorted(_BUILTIN_LOCALES)


__all__ = [
    "LocalePack",
    "TerminologySystemDef",
    "available_locales",
    "load_locale_pack",
]
