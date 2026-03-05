"""Tests for locale pack types, factory, AR pack, and FHIR awareness."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from saludai_core.exceptions import LocaleNotFoundError
from saludai_core.locales import (
    CustomOperationDef,
    ExtensionDef,
    FHIRProfileDef,
    IdentifierSystemDef,
    LocalePack,
    LocaleResourceConfig,
    TerminologySystemDef,
    available_locales,
    build_fhir_awareness_section,
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

    def test_default_uses_ar_pack(self) -> None:
        default_resolver = TerminologyResolver()
        pack_resolver = TerminologyResolver(locale_pack=AR_LOCALE_PACK)
        assert default_resolver.concept_count == pack_resolver.concept_count


# =====================================================================
# FHIR awareness types
# =====================================================================


class TestExtensionDef:
    """ExtensionDef is frozen and has expected fields."""

    def test_frozen(self) -> None:
        ext = ExtensionDef(
            url="http://example.com/ext",
            name="Test",
            description="A test extension",
            value_type="string",
            context="Patient",
        )
        with pytest.raises(AttributeError):
            ext.url = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        ext = ExtensionDef(
            url="http://example.com/ext",
            name="Test",
            description="desc",
            value_type="CodeableConcept",
            context="Patient",
        )
        assert ext.url == "http://example.com/ext"
        assert ext.value_type == "CodeableConcept"
        assert ext.context == "Patient"


class TestFHIRProfileDef:
    """FHIRProfileDef is frozen and supports mandatory extensions."""

    def test_frozen(self) -> None:
        p = FHIRProfileDef(
            resource_type="Patient",
            profile_url="http://example.com/Patient",
            name="Test",
            description="Test profile",
        )
        with pytest.raises(AttributeError):
            p.resource_type = "other"  # type: ignore[misc]

    def test_default_empty_extensions(self) -> None:
        p = FHIRProfileDef(
            resource_type="Patient",
            profile_url="http://example.com/Patient",
            name="Test",
            description="desc",
        )
        assert p.mandatory_extensions == ()

    def test_with_mandatory_extensions(self) -> None:
        ext = ExtensionDef(
            url="http://example.com/ext",
            name="E",
            description="d",
            value_type="string",
            context="Patient",
        )
        p = FHIRProfileDef(
            resource_type="Patient",
            profile_url="http://example.com/Patient",
            name="Test",
            description="desc",
            mandatory_extensions=(ext,),
        )
        assert len(p.mandatory_extensions) == 1
        assert p.mandatory_extensions[0].name == "E"


class TestCustomOperationDef:
    """CustomOperationDef is frozen."""

    def test_server_level(self) -> None:
        op = CustomOperationDef(
            name="$validate",
            resource_type=None,
            description="Validate",
        )
        assert op.resource_type is None

    def test_resource_level(self) -> None:
        op = CustomOperationDef(
            name="$summary",
            resource_type="Patient",
            description="IPS summary",
        )
        assert op.resource_type == "Patient"


class TestIdentifierSystemDef:
    """IdentifierSystemDef is frozen."""

    def test_fields(self) -> None:
        idef = IdentifierSystemDef(
            system_uri="http://example.com/dni",
            name="DNI",
            description="National ID",
            resource_types=("Patient",),
        )
        assert idef.name == "DNI"
        assert "Patient" in idef.resource_types

    def test_default_empty_resources(self) -> None:
        idef = IdentifierSystemDef(
            system_uri="http://example.com",
            name="Test",
            description="d",
        )
        assert idef.resource_types == ()


class TestLocaleResourceConfig:
    """LocaleResourceConfig is frozen."""

    def test_fields(self) -> None:
        rc = LocaleResourceConfig(
            resource_type="Patient",
            usage_note="Demographics",
            common_search_params=("identifier", "name"),
        )
        assert rc.resource_type == "Patient"
        assert "identifier" in rc.common_search_params


class TestLocalPackBackwardCompatibility:
    """LocalePack with only original fields still works."""

    def test_minimal_pack(self) -> None:
        pack = LocalePack(
            code="xx",
            name="Test",
            language="en",
            terminology_systems=(),
            system_prompt="test",
            tool_descriptions={},
            tool_system_enum=(),
        )
        assert pack.fhir_profiles == ()
        assert pack.extensions == ()
        assert pack.custom_operations == ()
        assert pack.custom_search_params == ()
        assert pack.identifier_systems == ()
        assert pack.resource_configs == ()
        assert pack.validation_notes == ""


# =====================================================================
# Prompt builder
# =====================================================================


class TestBuildFHIRAwarenessSection:
    """build_fhir_awareness_section generates correct prompt sections."""

    def test_empty_pack_returns_empty(self) -> None:
        pack = LocalePack(
            code="xx",
            name="Test",
            language="en",
            terminology_systems=(),
            system_prompt="test",
            tool_descriptions={},
            tool_system_enum=(),
        )
        assert build_fhir_awareness_section(pack) == ""

    def test_profiles_section(self) -> None:
        pack = LocalePack(
            code="xx",
            name="TestLand",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            fhir_profiles=(
                FHIRProfileDef(
                    resource_type="Patient",
                    profile_url="http://example.com/Patient",
                    name="Test Patient",
                    description="A test profile",
                ),
            ),
        )
        section = build_fhir_awareness_section(pack)
        assert "Perfiles FHIR locales (TestLand)" in section
        assert "Patient" in section
        assert "Test Patient" in section

    def test_profiles_with_extensions(self) -> None:
        ext = ExtensionDef(
            url="http://example.com/ext",
            name="MyExt",
            description="d",
            value_type="string",
            context="Patient",
        )
        pack = LocalePack(
            code="xx",
            name="T",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            fhir_profiles=(
                FHIRProfileDef(
                    resource_type="Patient",
                    profile_url="http://example.com/Patient",
                    name="P",
                    description="d",
                    mandatory_extensions=(ext,),
                ),
            ),
        )
        section = build_fhir_awareness_section(pack)
        assert "Extensiones obligatorias: MyExt" in section

    def test_extensions_section(self) -> None:
        pack = LocalePack(
            code="xx",
            name="T",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            extensions=(
                ExtensionDef(
                    url="http://example.com/ext",
                    name="Etnia",
                    description="Ethnic group",
                    value_type="CodeableConcept",
                    context="Patient",
                ),
            ),
        )
        section = build_fhir_awareness_section(pack)
        assert "Extensiones FHIR" in section
        assert "Etnia" in section
        assert "CodeableConcept" in section

    def test_identifier_systems_section(self) -> None:
        pack = LocalePack(
            code="xx",
            name="T",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            identifier_systems=(
                IdentifierSystemDef(
                    system_uri="http://example.com/dni",
                    name="DNI",
                    description="National ID",
                    resource_types=("Patient",),
                ),
            ),
        )
        section = build_fhir_awareness_section(pack)
        assert "Sistemas de identificacion" in section
        assert "DNI" in section
        assert "Patient" in section

    def test_operations_section(self) -> None:
        pack = LocalePack(
            code="xx",
            name="T",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            custom_operations=(
                CustomOperationDef(
                    name="$summary",
                    resource_type="Patient",
                    description="IPS summary",
                ),
            ),
        )
        section = build_fhir_awareness_section(pack)
        assert "Operaciones FHIR custom" in section
        assert "$summary" in section

    def test_resource_configs_section(self) -> None:
        pack = LocalePack(
            code="xx",
            name="TestLand",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            resource_configs=(
                LocaleResourceConfig(
                    resource_type="Patient",
                    usage_note="Demographics with DNI",
                    common_search_params=("identifier", "name"),
                ),
            ),
        )
        section = build_fhir_awareness_section(pack)
        assert "Recursos FHIR en TestLand" in section
        assert "identifier, name" in section

    def test_validation_notes_section(self) -> None:
        pack = LocalePack(
            code="xx",
            name="T",
            language="en",
            terminology_systems=(),
            system_prompt="",
            tool_descriptions={},
            tool_system_enum=(),
            validation_notes="Patient requires DNI",
        )
        section = build_fhir_awareness_section(pack)
        assert "Reglas de validacion locales" in section
        assert "Patient requires DNI" in section


# =====================================================================
# AR pack FHIR awareness
# =====================================================================


class TestARLocalePackFHIRAwareness:
    """AR pack includes real openRSD FHIR awareness data."""

    def test_has_profiles(self) -> None:
        assert len(AR_LOCALE_PACK.fhir_profiles) >= 5
        types = {p.resource_type for p in AR_LOCALE_PACK.fhir_profiles}
        assert "Patient" in types
        assert "Practitioner" in types
        assert "Immunization" in types

    def test_patient_profile_has_extensions(self) -> None:
        patient_profiles = [p for p in AR_LOCALE_PACK.fhir_profiles if p.resource_type == "Patient"]
        assert len(patient_profiles) == 1
        assert len(patient_profiles[0].mandatory_extensions) >= 2

    def test_has_extensions(self) -> None:
        assert len(AR_LOCALE_PACK.extensions) >= 5
        names = {e.name for e in AR_LOCALE_PACK.extensions}
        assert "Etnia" in names
        assert "Esquema NOMIVAC" in names

    def test_has_identifier_systems(self) -> None:
        assert len(AR_LOCALE_PACK.identifier_systems) >= 3
        names = {i.name for i in AR_LOCALE_PACK.identifier_systems}
        assert "DNI" in names
        assert "REFEPS" in names
        assert "REFES" in names

    def test_has_custom_operations(self) -> None:
        assert len(AR_LOCALE_PACK.custom_operations) >= 1
        op_names = {op.name for op in AR_LOCALE_PACK.custom_operations}
        assert "$summary" in op_names

    def test_has_resource_configs(self) -> None:
        assert len(AR_LOCALE_PACK.resource_configs) >= 6
        types = {rc.resource_type for rc in AR_LOCALE_PACK.resource_configs}
        assert "Patient" in types
        assert "Condition" in types
        assert "MedicationRequest" in types

    def test_has_validation_notes(self) -> None:
        assert "DNI" in AR_LOCALE_PACK.validation_notes
        assert "birthDate" in AR_LOCALE_PACK.validation_notes

    def test_system_prompt_includes_awareness(self) -> None:
        prompt = AR_LOCALE_PACK.system_prompt
        assert "Perfiles FHIR locales" in prompt
        assert "Extensiones FHIR" in prompt
        assert "Sistemas de identificacion" in prompt
        assert "Recursos FHIR en Argentina" in prompt

    def test_profile_urls_are_valid(self) -> None:
        for p in AR_LOCALE_PACK.fhir_profiles:
            assert p.profile_url.startswith("http")
            assert "StructureDefinition" in p.profile_url

    def test_extension_urls_are_valid(self) -> None:
        for e in AR_LOCALE_PACK.extensions:
            assert e.url.startswith("http")

    def test_identifier_uris_are_valid(self) -> None:
        for i in AR_LOCALE_PACK.identifier_systems:
            assert i.system_uri.startswith("http")


# =====================================================================
# Entry-point discovery
# =====================================================================

_FAKE_PACK = LocalePack(
    code="br",
    name="Brasil",
    language="pt",
    terminology_systems=(),
    system_prompt="test",
    tool_descriptions={},
    tool_system_enum=(),
)


def _make_entry_point(name: str, obj: object) -> MagicMock:
    """Create a fake ``importlib.metadata.EntryPoint``."""
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = obj
    return ep


class TestEntryPointDiscovery:
    """load_locale_pack discovers packs via entry points."""

    def test_discovers_external_pack(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ep = _make_entry_point("br", _FAKE_PACK)
        monkeypatch.setattr(
            "saludai_core.locales.importlib.metadata.entry_points",
            lambda group: [ep],
        )
        pack = load_locale_pack("br")
        assert pack.code == "br"
        assert pack.language == "pt"

    def test_builtin_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Built-in 'ar' is returned even if an entry point also provides 'ar'."""
        fake_ar = LocalePack(
            code="ar",
            name="Fake AR",
            language="es",
            terminology_systems=(),
            system_prompt="fake",
            tool_descriptions={},
            tool_system_enum=(),
        )
        ep = _make_entry_point("ar", fake_ar)
        monkeypatch.setattr(
            "saludai_core.locales.importlib.metadata.entry_points",
            lambda group: [ep],
        )
        pack = load_locale_pack("ar")
        # Should be the real AR pack, not the fake one
        assert pack.name == "Argentina"
        assert pack.system_prompt != "fake"

    def test_invalid_entry_point_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ep = _make_entry_point("xx", "not a LocalePack")
        monkeypatch.setattr(
            "saludai_core.locales.importlib.metadata.entry_points",
            lambda group: [ep],
        )
        with pytest.raises(LocaleNotFoundError, match="expected LocalePack"):
            load_locale_pack("xx")

    def test_not_found_with_no_entry_points(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "saludai_core.locales.importlib.metadata.entry_points",
            lambda group: [],
        )
        with pytest.raises(LocaleNotFoundError, match="zz"):
            load_locale_pack("zz")

    def test_available_locales_includes_entry_points(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ep = _make_entry_point("br", _FAKE_PACK)
        monkeypatch.setattr(
            "saludai_core.locales.importlib.metadata.entry_points",
            lambda group: [ep],
        )
        locales = available_locales()
        assert "ar" in locales
        assert "br" in locales

    def test_error_message_lists_all_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ep = _make_entry_point("br", _FAKE_PACK)
        monkeypatch.setattr(
            "saludai_core.locales.importlib.metadata.entry_points",
            lambda group: [ep],
        )
        with pytest.raises(LocaleNotFoundError, match=r"ar.*br"):
            load_locale_pack("zz")
