"""Tests for locale pack integration in the agent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest  # noqa: TC002 — used as fixture type

from saludai_agent.config import AgentConfig
from saludai_agent.loop import AgentLoop
from saludai_agent.prompts import SYSTEM_PROMPT
from saludai_agent.tools import ToolRegistry
from saludai_core.locales import load_locale_pack
from saludai_core.locales.ar import AR_LOCALE_PACK


class TestAgentConfigLocale:
    """AgentConfig has a locale field."""

    def test_default_locale_is_ar(self) -> None:
        config = AgentConfig()
        assert config.locale == "ar"

    def test_locale_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_LOCALE", "br")
        config = AgentConfig()
        assert config.locale == "br"


class TestToolRegistryWithLocalePack:
    """ToolRegistry uses locale pack for tool definitions."""

    def test_without_locale_pack(self) -> None:
        fhir_client = MagicMock()
        registry = ToolRegistry(fhir_client=fhir_client)
        defs = registry.definitions()
        assert len(defs) == 3  # no resolver

    def test_with_locale_pack(self) -> None:
        fhir_client = MagicMock()
        resolver = MagicMock()
        pack = load_locale_pack("ar")
        registry = ToolRegistry(
            fhir_client=fhir_client,
            terminology_resolver=resolver,
            locale_pack=pack,
        )
        defs = registry.definitions()
        assert len(defs) == 4

    def test_locale_pack_overrides_description(self) -> None:
        fhir_client = MagicMock()
        pack = load_locale_pack("ar")
        registry = ToolRegistry(fhir_client=fhir_client, locale_pack=pack)
        defs = {d["name"]: d for d in registry.definitions()}
        # Description should match the pack's description
        assert defs["search_fhir"]["description"] == pack.tool_descriptions["search_fhir"]

    def test_locale_pack_overrides_system_enum(self) -> None:
        fhir_client = MagicMock()
        resolver = MagicMock()
        pack = load_locale_pack("ar")
        registry = ToolRegistry(
            fhir_client=fhir_client,
            terminology_resolver=resolver,
            locale_pack=pack,
        )
        defs = {d["name"]: d for d in registry.definitions()}
        enum_vals = defs["resolve_terminology"]["input_schema"]["properties"]["system"]["enum"]
        assert enum_vals == list(pack.tool_system_enum)


class TestAgentLoopWithLocalePack:
    """AgentLoop uses locale pack system prompt."""

    def test_uses_pack_prompt(self) -> None:
        llm = MagicMock()
        fhir_client = MagicMock()
        pack = load_locale_pack("ar")
        loop = AgentLoop(
            llm=llm,
            fhir_client=fhir_client,
            locale_pack=pack,
        )
        assert loop._system_prompt == pack.system_prompt

    def test_default_uses_module_prompt(self) -> None:
        llm = MagicMock()
        fhir_client = MagicMock()
        loop = AgentLoop(llm=llm, fhir_client=fhir_client)
        assert loop._system_prompt == SYSTEM_PROMPT


class TestPromptsBackwardCompat:
    """prompts.py SYSTEM_PROMPT is backward compatible with AR pack."""

    def test_ar_pack_prompt_starts_with_base(self) -> None:
        assert AR_LOCALE_PACK.system_prompt.startswith(SYSTEM_PROMPT)

    def test_ar_pack_prompt_includes_awareness(self) -> None:
        assert "Perfiles FHIR locales" in AR_LOCALE_PACK.system_prompt

    def test_prompt_version_exists(self) -> None:
        from saludai_agent.prompts import PROMPT_VERSION

        assert PROMPT_VERSION == "v1.3"
