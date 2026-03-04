"""Tests for locale pack types, factory, and AR pack."""

from __future__ import annotations

import pytest

from saludai_core.exceptions import LocaleNotFoundError
from saludai_core.locales import (
    LocalePack,
    TerminologySystemDef,
    available_locales,
    load_locale_pack,
)
from saludai_core.locales.ar import AR_LOCALE_PACK
from saludai_core.terminology import TerminologyResolver, TerminologySystem


class TestTerminologySystemDef:
    """TerminologySystemDef is frozen and has expected fields."""

    def test_frozen(self) -> None:
        sys_def = TerminologySystemDef(
            key="test",
            system_uri="http://example.com",
            csv_filename="test.csv",
            display_name="Test System",
            data_package="some.package",
        )
        with pytest.raises(AttributeError):
            sys_def.key = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        sys_def = TerminologySystemDef(
            key="snomed_ct",
            system_uri="http://snomed.info/sct",
            csv_filename="snomed_ar.csv",
            display_name="SNOMED CT",
            data_package="saludai_core.locales.ar",
        )
        assert sys_def.key == "snomed_ct"
        assert sys_def.system_uri == "http://snomed.info/sct"
        assert sys_def.csv_filename == "snomed_ar.csv"


class TestLocalePack:
    """LocalePack is frozen and has expected fields."""

    def test_frozen(self) -> None:
        pack = LocalePack(
            code="test",
            name="Test",
            language="en",
            terminology_systems=(),
            system_prompt="test",
            tool_descriptions={},
            tool_system_enum=(),
        )
        with pytest.raises(AttributeError):
            pack.code = "other"  # type: ignore[misc]


class TestLoadLocalePack:
    """load_locale_pack factory."""

    def test_load_ar(self) -> None:
        pack = load_locale_pack("ar")
        assert isinstance(pack, LocalePack)
        assert pack.code == "ar"

    def test_load_default_is_ar(self) -> None:
        pack = load_locale_pack()
        assert pack.code == "ar"

    def test_load_unknown_raises(self) -> None:
        with pytest.raises(LocaleNotFoundError, match="xx"):
            load_locale_pack("xx")

    def test_available_locales(self) -> None:
        locales = available_locales()
        assert "ar" in locales
        assert isinstance(locales, list)


class TestARLocalePack:
    """AR locale pack has all required content."""

    def test_code(self) -> None:
        assert AR_LOCALE_PACK.code == "ar"

    def test_name(self) -> None:
        assert AR_LOCALE_PACK.name == "Argentina"

    def test_language(self) -> None:
        assert AR_LOCALE_PACK.language == "es"

    def test_has_three_terminology_systems(self) -> None:
        assert len(AR_LOCALE_PACK.terminology_systems) == 3

    def test_terminology_system_keys(self) -> None:
        keys = {s.key for s in AR_LOCALE_PACK.terminology_systems}
        assert keys == {"snomed_ct", "cie_10", "loinc"}

    def test_terminology_system_uris(self) -> None:
        uris = {s.system_uri for s in AR_LOCALE_PACK.terminology_systems}
        assert "http://snomed.info/sct" in uris
        assert "http://hl7.org/fhir/sid/icd-10" in uris
        assert "http://loinc.org" in uris

    def test_system_prompt_not_empty(self) -> None:
        assert len(AR_LOCALE_PACK.system_prompt) > 100

    def test_system_prompt_mentions_argentina(self) -> None:
        assert "argentino" in AR_LOCALE_PACK.system_prompt.lower()

    def test_tool_descriptions_has_all_tools(self) -> None:
        expected = {"resolve_terminology", "search_fhir", "get_resource", "execute_code"}
        assert set(AR_LOCALE_PACK.tool_descriptions.keys()) == expected

    def test_tool_system_enum(self) -> None:
        assert AR_LOCALE_PACK.tool_system_enum == ("snomed_ct", "cie_10", "loinc")

    def test_data_packages_point_to_ar(self) -> None:
        for sys_def in AR_LOCALE_PACK.terminology_systems:
            assert sys_def.data_package == "saludai_core.locales.ar"


class TestTerminologyResolverWithLocalePack:
    """TerminologyResolver loads data from locale pack CSVs."""

    def test_loads_from_locale_pack(self) -> None:
        resolver = TerminologyResolver(locale_pack=AR_LOCALE_PACK)
        assert resolver.concept_count > 0

    def test_resolves_snomed_from_pack(self) -> None:
        resolver = TerminologyResolver(locale_pack=AR_LOCALE_PACK)
        match = resolver.resolve("diabetes tipo 2", system=TerminologySystem.SNOMED_CT)
        assert match.concept is not None
        assert match.concept.code == "44054006"

    def test_same_results_as_default(self) -> None:
        default_resolver = TerminologyResolver()
        pack_resolver = TerminologyResolver(locale_pack=AR_LOCALE_PACK)
        assert default_resolver.concept_count == pack_resolver.concept_count
