"""Tests for the English (US) locale pack."""

from __future__ import annotations

from saludai_core.locales import (
    available_locales,
    load_locale_pack,
)
from saludai_core.locales.en_us import EN_US_LOCALE_PACK
from saludai_core.terminology import TerminologyResolver, TerminologySystem


class TestLoadENUS:
    """load_locale_pack recognizes 'en_us'."""

    def test_load_en_us(self) -> None:
        pack = load_locale_pack("en_us")
        assert pack.code == "en_us"

    def test_available_locales_includes_en_us(self) -> None:
        locales = available_locales()
        assert "en_us" in locales
        assert "ar" in locales


class TestENUSLocalePack:
    """EN_US locale pack has all required content."""

    def test_code(self) -> None:
        assert EN_US_LOCALE_PACK.code == "en_us"

    def test_name(self) -> None:
        assert EN_US_LOCALE_PACK.name == "United States"

    def test_language(self) -> None:
        assert EN_US_LOCALE_PACK.language == "en"

    def test_has_four_terminology_systems(self) -> None:
        assert len(EN_US_LOCALE_PACK.terminology_systems) == 4

    def test_terminology_system_keys(self) -> None:
        keys = {s.key for s in EN_US_LOCALE_PACK.terminology_systems}
        assert keys == {"snomed_ct", "icd_10_cm", "loinc", "atc"}

    def test_terminology_system_uris(self) -> None:
        uris = {s.system_uri for s in EN_US_LOCALE_PACK.terminology_systems}
        assert "http://snomed.info/sct" in uris
        assert "http://hl7.org/fhir/sid/icd-10-cm" in uris
        assert "http://loinc.org" in uris
        assert "http://www.whocc.no/atc" in uris

    def test_system_prompt_not_empty(self) -> None:
        assert len(EN_US_LOCALE_PACK.system_prompt) > 100

    def test_system_prompt_mentions_united_states(self) -> None:
        assert "united states" in EN_US_LOCALE_PACK.system_prompt.lower()

    def test_system_prompt_in_english(self) -> None:
        prompt = EN_US_LOCALE_PACK.system_prompt
        assert "You are a health data agent" in prompt

    def test_tool_descriptions_has_all_tools(self) -> None:
        expected = {
            "resolve_terminology",
            "search_fhir",
            "count_fhir",
            "get_resource",
            "execute_code",
        }
        assert set(EN_US_LOCALE_PACK.tool_descriptions.keys()) == expected

    def test_tool_system_enum(self) -> None:
        assert EN_US_LOCALE_PACK.tool_system_enum == ("snomed_ct", "icd_10_cm", "loinc", "atc")

    def test_data_packages_point_to_en_us(self) -> None:
        for sys_def in EN_US_LOCALE_PACK.terminology_systems:
            assert sys_def.data_package == "saludai_core.locales.en_us"


class TestENUSFHIRAwareness:
    """EN_US pack includes US Core FHIR awareness data."""

    def test_has_profiles(self) -> None:
        assert len(EN_US_LOCALE_PACK.fhir_profiles) >= 5
        types = {p.resource_type for p in EN_US_LOCALE_PACK.fhir_profiles}
        assert "Patient" in types
        assert "Encounter" in types
        assert "Condition" in types

    def test_patient_profile_has_extensions(self) -> None:
        patient_profiles = [
            p for p in EN_US_LOCALE_PACK.fhir_profiles if p.resource_type == "Patient"
        ]
        assert len(patient_profiles) == 1
        assert len(patient_profiles[0].mandatory_extensions) >= 3

    def test_has_us_core_extensions(self) -> None:
        assert len(EN_US_LOCALE_PACK.extensions) >= 3
        names = {e.name for e in EN_US_LOCALE_PACK.extensions}
        assert "Race" in names
        assert "Ethnicity" in names
        assert "Birth Sex" in names

    def test_has_identifier_systems(self) -> None:
        assert len(EN_US_LOCALE_PACK.identifier_systems) >= 3
        names = {i.name for i in EN_US_LOCALE_PACK.identifier_systems}
        assert "SSN" in names
        assert "NPI" in names
        assert "MRN" in names

    def test_has_resource_configs(self) -> None:
        assert len(EN_US_LOCALE_PACK.resource_configs) >= 10
        types = {rc.resource_type for rc in EN_US_LOCALE_PACK.resource_configs}
        assert "Patient" in types
        assert "Condition" in types
        assert "MedicationRequest" in types
        assert "CarePlan" in types

    def test_has_resource_relationships(self) -> None:
        assert len(EN_US_LOCALE_PACK.resource_relationships) == 10

    def test_has_query_patterns(self) -> None:
        assert len(EN_US_LOCALE_PACK.query_patterns) == 11

    def test_has_validation_notes(self) -> None:
        assert "US Core" in EN_US_LOCALE_PACK.validation_notes

    def test_system_prompt_includes_awareness(self) -> None:
        prompt = EN_US_LOCALE_PACK.system_prompt
        assert "United States" in prompt
        assert "US Core Patient" in prompt
        assert "SSN" in prompt

    def test_profile_urls_are_valid(self) -> None:
        for p in EN_US_LOCALE_PACK.fhir_profiles:
            assert p.profile_url.startswith("http")
            assert "StructureDefinition" in p.profile_url

    def test_extension_urls_are_valid(self) -> None:
        for e in EN_US_LOCALE_PACK.extensions:
            assert e.url.startswith("http")

    def test_identifier_uris_are_valid(self) -> None:
        for i in EN_US_LOCALE_PACK.identifier_systems:
            assert i.system_uri.startswith("http")

    def test_query_patterns_in_english(self) -> None:
        for qp in EN_US_LOCALE_PACK.query_patterns:
            # Example questions should not be in Spanish
            assert "Cuantos" not in qp.example_question
            assert "pacientes" not in qp.example_question.lower()


class TestTerminologyResolverENUS:
    """TerminologyResolver loads data from EN_US locale pack CSVs."""

    def test_loads_from_locale_pack(self) -> None:
        resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        assert resolver.concept_count > 0

    def test_resolves_snomed_diabetes(self) -> None:
        resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        match = resolver.resolve("type 2 diabetes", system=TerminologySystem.SNOMED_CT)
        assert match.concept is not None
        assert match.concept.code == "44054006"

    def test_resolves_snomed_hypertension(self) -> None:
        resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        match = resolver.resolve("essential hypertension", system=TerminologySystem.SNOMED_CT)
        assert match.concept is not None
        assert match.concept.code == "59621000"

    def test_resolves_icd10cm(self) -> None:
        resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        match = resolver.resolve("type 2 diabetes", system=TerminologySystem.ICD_10_CM)
        assert match.concept is not None
        assert match.concept.code == "E11"

    def test_resolves_loinc(self) -> None:
        resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        match = resolver.resolve("HbA1c", system=TerminologySystem.LOINC)
        assert match.concept is not None
        assert match.concept.code == "4548-4"

    def test_resolves_atc(self) -> None:
        resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        match = resolver.resolve("metformin", system=TerminologySystem.ATC)
        assert match.concept is not None
        assert match.concept.code == "A10BA02"

    def test_concept_count_matches_ar(self) -> None:
        """EN_US should have the same number of concepts as AR."""
        from saludai_core.locales.ar import AR_LOCALE_PACK

        ar_resolver = TerminologyResolver(locale_pack=AR_LOCALE_PACK)
        en_resolver = TerminologyResolver(locale_pack=EN_US_LOCALE_PACK)
        assert en_resolver.concept_count == ar_resolver.concept_count
