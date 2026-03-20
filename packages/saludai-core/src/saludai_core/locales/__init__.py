"""Locale pack registry and loader.

Use ``load_locale_pack(code)`` to obtain a ``LocalePack`` for a given locale.
Ships with ``"ar"`` (Argentina) as the default and only built-in locale.
External packages can register additional locales via the
``saludai.locales`` entry-point group::

    # In your package's pyproject.toml:
    [project.entry-points."saludai.locales"]
    br = "my_package.locale_br:BR_LOCALE_PACK"

The entry point must resolve to a ``LocalePack`` instance.  Built-in packs
take precedence over entry-point packs with the same code.
"""

from __future__ import annotations

import importlib.metadata
import logging

from saludai_core.exceptions import LocaleNotFoundError
from saludai_core.locales._prompt_builder import build_fhir_awareness_section
from saludai_core.locales._types import (
    CustomOperationDef,
    CustomSearchParamDef,
    ExtensionDef,
    FHIRProfileDef,
    IdentifierSystemDef,
    LocalePack,
    LocaleResourceConfig,
    QueryPattern,
    ResourceRelationship,
    TerminologySystemDef,
)

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUP = "saludai.locales"

# ---------------------------------------------------------------------------
# Built-in locale registry (lazy — imported on first access)
# ---------------------------------------------------------------------------

_BUILTIN_LOCALES: frozenset[str] = frozenset({"ar"})


def _discover_entry_point(code: str) -> LocalePack | None:
    """Try to load a locale pack from installed entry points.

    Returns:
        The ``LocalePack`` if found and valid, otherwise ``None``.
    """
    eps = importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP)
    for ep in eps:
        if ep.name == code:
            obj = ep.load()
            if not isinstance(obj, LocalePack):
                msg = (
                    f"Entry point {_ENTRY_POINT_GROUP}:{code!r} resolved to "
                    f"{type(obj).__name__}, expected LocalePack"
                )
                raise LocaleNotFoundError(msg)
            return obj
    return None


def _discover_entry_point_codes() -> set[str]:
    """Return locale codes registered via entry points."""
    eps = importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP)
    return {ep.name for ep in eps}


def load_locale_pack(code: str = "ar") -> LocalePack:
    """Load a locale pack by its code.

    Resolution order:

    1. Built-in packs (currently only ``"ar"``).
    2. Entry points registered under the ``saludai.locales`` group.

    Args:
        code: Locale code (e.g. ``"ar"``).  Defaults to ``"ar"``.

    Returns:
        The corresponding ``LocalePack``.

    Raises:
        LocaleNotFoundError: If no pack exists for the given code, or if
            the entry point does not resolve to a ``LocalePack``.
    """
    # 1. Built-in packs (fast path, no importlib.metadata overhead)
    if code == "ar":
        from saludai_core.locales.ar import AR_LOCALE_PACK

        return AR_LOCALE_PACK

    # 2. Entry-point discovery
    pack = _discover_entry_point(code)
    if pack is not None:
        return pack

    all_codes = sorted(_BUILTIN_LOCALES | _discover_entry_point_codes())
    raise LocaleNotFoundError(f"Locale pack {code!r} not found. Available locales: {all_codes}")


def available_locales() -> list[str]:
    """Return codes of all available locale packs (built-in + entry points)."""
    return sorted(_BUILTIN_LOCALES | _discover_entry_point_codes())


__all__ = [
    "CustomOperationDef",
    "CustomSearchParamDef",
    "ExtensionDef",
    "FHIRProfileDef",
    "IdentifierSystemDef",
    "LocalePack",
    "LocaleResourceConfig",
    "QueryPattern",
    "ResourceRelationship",
    "TerminologySystemDef",
    "available_locales",
    "build_fhir_awareness_section",
    "load_locale_pack",
]
