"""Tests for saludai_agent.prompts."""

from __future__ import annotations

from saludai_agent.prompts import PROMPT_VERSION, SYSTEM_PROMPT


class TestSystemPrompt:
    """System prompt contains required instructions."""

    def test_not_empty(self) -> None:
        assert len(SYSTEM_PROMPT) > 100

    def test_mentions_resolve_terminology(self) -> None:
        assert "resolve_terminology" in SYSTEM_PROMPT

    def test_mentions_search_fhir(self) -> None:
        assert "search_fhir" in SYSTEM_PROMPT

    def test_mentions_fhir_r4(self) -> None:
        assert "FHIR R4" in SYSTEM_PROMPT

    def test_mentions_snomed(self) -> None:
        assert "SNOMED" in SYSTEM_PROMPT

    def test_mentions_cie10(self) -> None:
        assert "CIE-10" in SYSTEM_PROMPT

    def test_mentions_loinc(self) -> None:
        assert "LOINC" in SYSTEM_PROMPT

    def test_mentions_never_invent_codes(self) -> None:
        assert "inventes" in SYSTEM_PROMPT.lower() or "nunca" in SYSTEM_PROMPT.lower()

    def test_mentions_auditability(self) -> None:
        assert "auditabilidad" in SYSTEM_PROMPT.lower()

    def test_mentions_get_resource(self) -> None:
        assert "get_resource" in SYSTEM_PROMPT

    def test_mentions_execute_code(self) -> None:
        assert "execute_code" in SYSTEM_PROMPT

    def test_mentions_data_processing(self) -> None:
        assert "entries" in SYSTEM_PROMPT and "store" in SYSTEM_PROMPT

    def test_mentions_include(self) -> None:
        assert "_include" in SYSTEM_PROMPT

    def test_instructs_same_language(self) -> None:
        assert "idioma" in SYSTEM_PROMPT

    def test_mentions_count_fhir(self) -> None:
        assert "count_fhir" in SYSTEM_PROMPT


class TestPromptVersion:
    """Prompt version is a non-empty string."""

    def test_version_format(self) -> None:
        assert PROMPT_VERSION.startswith("v")
        assert "." in PROMPT_VERSION

    def test_current_version(self) -> None:
        assert PROMPT_VERSION == "v2.1"
