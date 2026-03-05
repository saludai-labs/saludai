"""Tests for the TerminologyResolver."""

from __future__ import annotations

import pytest

from saludai_core.exceptions import TerminologyCodeNotFoundError
from saludai_core.terminology import (
    EXACT_MATCH_SCORE,
    FUZZY_MATCH_THRESHOLD,
    MatchType,
    TerminologyConcept,
    TerminologyConfig,
    TerminologyResolver,
    TerminologySystem,
)


@pytest.fixture
def resolver() -> TerminologyResolver:
    """Create a default TerminologyResolver."""
    return TerminologyResolver()


# -----------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------


class TestDataLoading:
    """Tests for CSV data loading."""

    def test_loads_snomed(self, resolver: TerminologyResolver) -> None:
        snomed = [c for c in resolver._concepts if c.system == TerminologySystem.SNOMED_CT]
        assert len(snomed) >= 90

    def test_loads_cie10(self, resolver: TerminologyResolver) -> None:
        cie10 = [c for c in resolver._concepts if c.system == TerminologySystem.CIE_10]
        assert len(cie10) >= 30

    def test_loads_loinc(self, resolver: TerminologyResolver) -> None:
        loinc = [c for c in resolver._concepts if c.system == TerminologySystem.LOINC]
        assert len(loinc) >= 25

    def test_get_systems_returns_all_three(self, resolver: TerminologyResolver) -> None:
        systems = resolver.get_systems()
        assert TerminologySystem.SNOMED_CT in systems
        assert TerminologySystem.CIE_10 in systems
        assert TerminologySystem.LOINC in systems

    def test_extra_concepts_loaded(self) -> None:
        extra = TerminologyConcept(
            code="999999",
            system=TerminologySystem.SNOMED_CT,
            display="Concepto de prueba",
            display_en="Test concept",
            aliases=("prueba", "test"),
        )
        resolver = TerminologyResolver(extra_concepts=[extra])
        result = resolver.lookup("999999", TerminologySystem.SNOMED_CT)
        assert result.code == "999999"


# -----------------------------------------------------------------------
# Exact match
# -----------------------------------------------------------------------


class TestExactMatch:
    """Tests for exact matching (display names and aliases)."""

    def test_exact_display_spanish(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("Diabetes mellitus tipo 2")
        assert match.concept is not None
        assert match.concept.code == "44054006"
        assert match.score == EXACT_MATCH_SCORE
        assert match.match_type == MatchType.EXACT_DISPLAY

    def test_exact_display_case_insensitive(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("diabetes mellitus tipo 2")
        assert match.concept is not None
        assert match.concept.code == "44054006"
        assert match.score == EXACT_MATCH_SCORE

    def test_exact_alias(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("diabetes tipo 2")
        assert match.concept is not None
        assert match.concept.code == "44054006"
        assert match.match_type == MatchType.EXACT_ALIAS
        assert match.score == EXACT_MATCH_SCORE

    def test_exact_colloquial_alias(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("presión alta")
        assert match.concept is not None
        assert match.concept.code == "59621000"
        assert match.score == EXACT_MATCH_SCORE

    def test_exact_english_display(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("Type 2 diabetes mellitus")
        assert match.concept is not None
        assert match.concept.code == "44054006"
        assert match.match_type == MatchType.EXACT_DISPLAY

    def test_exact_score_is_max(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("Asma")
        assert match.score == EXACT_MATCH_SCORE
        assert match.is_confident is True

    def test_exact_filter_by_system(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("Diabetes mellitus tipo 2", system=TerminologySystem.CIE_10)
        assert match.concept is not None
        assert match.concept.system == TerminologySystem.CIE_10

    def test_hipertension_arterial_resolves_essential(self, resolver: TerminologyResolver) -> None:
        """'hipertensión arterial' MUST resolve to 59621000 (esencial), not 38341003."""
        match = resolver.resolve("hipertensión arterial")
        assert match.concept is not None
        assert match.concept.code == "59621000"

    def test_exact_cie10(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("Hipertensión esencial", system=TerminologySystem.CIE_10)
        assert match.concept is not None
        assert match.concept.code == "I10"
        assert match.score == EXACT_MATCH_SCORE


# -----------------------------------------------------------------------
# Fuzzy match
# -----------------------------------------------------------------------


class TestFuzzyMatch:
    """Tests for fuzzy matching."""

    def test_fuzzy_typo(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("diabetis mellitus tipo 2")
        assert match.concept is not None
        assert match.concept.code == "44054006"
        assert match.match_type == MatchType.FUZZY
        assert match.score >= FUZZY_MATCH_THRESHOLD

    def test_fuzzy_partial(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("insuficiencia cardiaca")
        assert match.concept is not None
        assert match.concept.code == "84114007"

    def test_fuzzy_word_order(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("tipo 2 diabetes")
        assert match.concept is not None
        assert match.concept.code == "44054006"

    def test_fuzzy_score_above_threshold(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("diabetis tipo 2")
        assert match.concept is not None
        assert match.score >= FUZZY_MATCH_THRESHOLD

    def test_fuzzy_accented_variant(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("hipertensión")
        assert match.concept is not None
        assert match.concept.code == "59621000"

    def test_fuzzy_abbreviation(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("EPOC")
        assert match.concept is not None
        assert match.concept.code == "13645005"

    def test_fuzzy_low_confidence_flagged(self, resolver: TerminologyResolver) -> None:
        # A term that matches fuzzily but with score in the review range
        # (between LOW_CONFIDENCE_THRESHOLD and FUZZY_MATCH_THRESHOLD)
        match = resolver.resolve("card")
        if match.match_type == MatchType.FUZZY and match.score < FUZZY_MATCH_THRESHOLD:
            assert match.needs_review is True

    def test_fuzzy_filter_by_system(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("glucosa", system=TerminologySystem.LOINC)
        assert match.concept is not None
        assert match.concept.system == TerminologySystem.LOINC


# -----------------------------------------------------------------------
# No match
# -----------------------------------------------------------------------


class TestNoMatch:
    """Tests for terms that should not match."""

    def test_gibberish_returns_no_match(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("xyzzyplugh12345")
        assert match.match_type == MatchType.NO_MATCH

    def test_no_match_concept_is_none(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("xyzzyplugh12345")
        assert match.concept is None

    def test_no_match_not_confident(self, resolver: TerminologyResolver) -> None:
        match = resolver.resolve("xyzzyplugh12345")
        assert match.is_confident is False


# -----------------------------------------------------------------------
# Search
# -----------------------------------------------------------------------


class TestSearch:
    """Tests for multi-result search."""

    def test_search_multiple_results(self, resolver: TerminologyResolver) -> None:
        results = resolver.search("diabetes")
        assert len(results) >= 2

    def test_search_sorted_by_score(self, resolver: TerminologyResolver) -> None:
        results = resolver.search("diabetes")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_respects_max_results(self, resolver: TerminologyResolver) -> None:
        results = resolver.search("diabetes", max_results=2)
        assert len(results) <= 2


# -----------------------------------------------------------------------
# Lookup
# -----------------------------------------------------------------------


class TestLookup:
    """Tests for code-based lookup."""

    def test_lookup_existing_code(self, resolver: TerminologyResolver) -> None:
        concept = resolver.lookup("44054006", TerminologySystem.SNOMED_CT)
        assert concept.code == "44054006"
        assert concept.display == "Diabetes mellitus tipo 2"

    def test_lookup_nonexistent_raises(self, resolver: TerminologyResolver) -> None:
        with pytest.raises(TerminologyCodeNotFoundError):
            resolver.lookup("00000000", TerminologySystem.SNOMED_CT)


# -----------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------


class TestCache:
    """Tests for the LRU resolution cache."""

    def test_cache_hit(self, resolver: TerminologyResolver) -> None:
        match1 = resolver.resolve("diabetes tipo 2")
        match2 = resolver.resolve("diabetes tipo 2")
        assert match1 == match2
        assert len(resolver._cache) == 1

    def test_cache_clear(self, resolver: TerminologyResolver) -> None:
        resolver.resolve("diabetes tipo 2")
        assert len(resolver._cache) == 1
        resolver.clear_cache()
        assert len(resolver._cache) == 0

    def test_cache_eviction(self) -> None:
        config = TerminologyConfig(cache_size=2)
        resolver = TerminologyResolver(config=config)
        resolver.resolve("diabetes tipo 2")
        resolver.resolve("hipertensión")
        resolver.resolve("asma")
        # First entry should have been evicted
        assert len(resolver._cache) == 2


# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------


class TestConfig:
    """Tests for TerminologyConfig."""

    def test_default_config(self) -> None:
        config = TerminologyConfig()
        assert config.fuzzy_threshold == FUZZY_MATCH_THRESHOLD
        assert config.low_confidence_threshold > 0
        assert config.cache_size > 0

    def test_custom_threshold(self) -> None:
        config = TerminologyConfig(fuzzy_threshold=80.0)
        resolver = TerminologyResolver(config=config)
        assert resolver._config.fuzzy_threshold == 80.0


# -----------------------------------------------------------------------
# Golden test
# -----------------------------------------------------------------------


class TestGolden:
    """The canonical acceptance test for the terminology resolver."""

    def test_diabetes_tipo_2_golden(self, resolver: TerminologyResolver) -> None:
        """'diabetes tipo 2' MUST resolve to SNOMED 44054006 with confidence."""
        match = resolver.resolve("diabetes tipo 2")
        assert match.concept is not None
        assert match.concept.code == "44054006"
        assert match.concept.system == TerminologySystem.SNOMED_CT
        assert match.is_confident is True
        assert match.needs_review is False
