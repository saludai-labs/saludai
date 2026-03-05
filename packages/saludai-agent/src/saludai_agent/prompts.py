"""System prompts for the FHIR healthcare data agent.

The canonical system prompt now lives in the AR locale pack
(``saludai_core.locales.ar._prompt``).  This module re-exports it for
backward compatibility so that existing imports continue to work.
"""

from __future__ import annotations

from saludai_core.locales.ar._prompt import SYSTEM_PROMPT_AR

PROMPT_VERSION: str = "v1.3"

SYSTEM_PROMPT: str = SYSTEM_PROMPT_AR
