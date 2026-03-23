"""Terminology resolver for clinical concept lookup.

Resolves natural-language clinical terms (in Spanish or English) to standard
terminology codes (SNOMED CT, CIE-10, LOINC) using a multi-strategy approach:

1. Exact match on display name or aliases (case-insensitive)
2. Fuzzy match via rapidfuzz (token_sort_ratio + partial_ratio)
3. LLM-assisted resolution (planned — not yet implemented)

All data is loaded from CSV files bundled with the package at init time.
Lookups are CPU-only (no I/O), so the public API is synchronous.
"""

from __future__ import annotations

import csv
import enum
from collections import OrderedDict
from dataclasses import dataclass
from importlib import resources
from typing import TYPE_CHECKING

import structlog
from rapidfuzz import fuzz

from saludai_core.exceptions import (
    TerminologyCodeNotFoundError,
    TerminologyDataError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from saludai_core.locales._types import LocalePack

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXACT_MATCH_SCORE: float = 100.0
FUZZY_MATCH_THRESHOLD: float = 70.0
LOW_CONFIDENCE_THRESHOLD: float = 55.0
DEFAULT_CACHE_SIZE: int = 256
DEFAULT_MAX_RESULTS: int = 5


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TerminologySystem(enum.StrEnum):
    """Standard terminology code systems with their FHIR URIs."""

    SNOMED_CT = "http://snomed.info/sct"
    CIE_10 = "http://hl7.org/fhir/sid/icd-10"
    LOINC = "http://loinc.org"
    ATC = "http://www.whocc.no/atc"


class MatchType(enum.StrEnum):
    """How a terminology match was found."""

    EXACT_DISPLAY = "exact_display"
    EXACT_ALIAS = "exact_alias"
    FUZZY = "fuzzy"
    NO_MATCH = "no_match"


# ---------------------------------------------------------------------------
# System → CSV file mapping
# ---------------------------------------------------------------------------

_DEFAULT_LOCALE = "ar"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TerminologyConcept:
    """A single concept in a terminology system."""

    code: str
    system: TerminologySystem
    display: str
    display_en: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TerminologyMatch:
    """Result of resolving a clinical term."""

    concept: TerminologyConcept | None
    score: float
    match_type: MatchType
    query: str

    @property
    def is_confident(self) -> bool:
        """Whether the match score is above the fuzzy threshold."""
        return self.score >= FUZZY_MATCH_THRESHOLD

    @property
    def needs_review(self) -> bool:
        """Whether the match is low-confidence and should be flagged."""
        if self.match_type == MatchType.NO_MATCH:
            return True
        return LOW_CONFIDENCE_THRESHOLD <= self.score < FUZZY_MATCH_THRESHOLD


@dataclass(frozen=True, slots=True)
class TerminologyConfig:
    """Configuration for the TerminologyResolver."""

    fuzzy_threshold: float = FUZZY_MATCH_THRESHOLD
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD
    cache_size: int = DEFAULT_CACHE_SIZE
    max_results: int = DEFAULT_MAX_RESULTS


# ---------------------------------------------------------------------------
# LRU Cache (OrderedDict-based)
# ---------------------------------------------------------------------------


class _LRUCache:
    """Simple LRU cache backed by an OrderedDict."""

    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._cache: OrderedDict[str, TerminologyMatch] = OrderedDict()

    def get(self, key: str) -> TerminologyMatch | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: TerminologyMatch) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


# ---------------------------------------------------------------------------
# Terminology Resolver
# ---------------------------------------------------------------------------


class TerminologyResolver:
    """Resolves natural-language clinical terms to standard codes.

    Loads terminology data from bundled CSV files at construction time.
    All public methods are synchronous (CPU-only, no I/O after init).

    Args:
        config: Optional configuration overrides.
        extra_concepts: Additional concepts to register beyond the CSV data.
    """

    def __init__(
        self,
        config: TerminologyConfig | None = None,
        extra_concepts: Sequence[TerminologyConcept] | None = None,
        locale_pack: LocalePack | None = None,
    ) -> None:
        self._config = config or TerminologyConfig()
        self._concepts: list[TerminologyConcept] = []
        self._by_code: dict[tuple[str, TerminologySystem], TerminologyConcept] = {}
        self._by_system: dict[TerminologySystem, list[TerminologyConcept]] = {
            s: [] for s in TerminologySystem
        }
        self._cache = _LRUCache(self._config.cache_size)

        if locale_pack is None:
            from saludai_core.locales.ar import AR_LOCALE_PACK

            locale_pack = AR_LOCALE_PACK
        self._load_from_locale_pack(locale_pack)

        if extra_concepts:
            for concept in extra_concepts:
                self._register_concept(concept)

        logger.info(
            "terminology_resolver_initialized",
            total_concepts=len(self._concepts),
            systems={s.name: len(v) for s, v in self._by_system.items()},
        )

    # -- Public API ---------------------------------------------------------

    def resolve(
        self,
        term: str,
        system: TerminologySystem | None = None,
    ) -> TerminologyMatch:
        """Resolve a clinical term to the best matching concept.

        Args:
            term: Natural-language clinical term (e.g. "diabetes tipo 2").
            system: Optionally restrict to a single terminology system.

        Returns:
            A ``TerminologyMatch`` with the best result (or NO_MATCH).
        """
        cache_key = self._cache_key(term, system)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("terminology_cache_hit", term=term, system=system)
            return cached

        candidates = self._get_candidates(system)
        match = self._find_best_match(term, candidates)

        self._cache.put(cache_key, match)
        logger.info(
            "terminology_resolved",
            term=term,
            code=match.concept.code if match.concept else None,
            score=match.score,
            match_type=match.match_type,
        )
        return match

    def search(
        self,
        term: str,
        system: TerminologySystem | None = None,
        max_results: int | None = None,
    ) -> list[TerminologyMatch]:
        """Search for multiple matching concepts, ranked by score.

        Args:
            term: Natural-language clinical term.
            system: Optionally restrict to a single terminology system.
            max_results: Maximum number of results to return.

        Returns:
            List of ``TerminologyMatch`` objects sorted by descending score.
        """
        limit = max_results or self._config.max_results
        candidates = self._get_candidates(system)
        matches = self._score_all(term, candidates)

        # Filter out NO_MATCH (score below low_confidence_threshold)
        matches = [m for m in matches if m.score >= self._config.low_confidence_threshold]
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def lookup(
        self,
        code: str,
        system: TerminologySystem,
    ) -> TerminologyConcept:
        """Look up a concept by its code and system.

        Args:
            code: The terminology code (e.g. "44054006").
            system: The terminology system.

        Returns:
            The matching ``TerminologyConcept``.

        Raises:
            TerminologyCodeNotFoundError: If the code is not found.
        """
        concept = self._by_code.get((code, system))
        if concept is None:
            raise TerminologyCodeNotFoundError(f"Code {code!r} not found in {system.name}")
        return concept

    def get_systems(self) -> list[TerminologySystem]:
        """Return all loaded terminology systems."""
        return [s for s in TerminologySystem if self._by_system[s]]

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()
        logger.debug("terminology_cache_cleared")

    @property
    def concept_count(self) -> int:
        """Total number of loaded concepts."""
        return len(self._concepts)

    # -- Internal -----------------------------------------------------------

    def _register_concept(self, concept: TerminologyConcept) -> None:
        """Register a concept in the internal indexes."""
        key = (concept.code, concept.system)
        if key not in self._by_code:
            self._concepts.append(concept)
            self._by_code[key] = concept
            self._by_system[concept.system].append(concept)

    def _get_candidates(self, system: TerminologySystem | None) -> list[TerminologyConcept]:
        if system is not None:
            return self._by_system[system]
        return self._concepts

    @staticmethod
    def _cache_key(term: str, system: TerminologySystem | None) -> str:
        normalized = term.strip().lower()
        sys_key = system.value if system else "*"
        return f"{sys_key}::{normalized}"

    def _find_best_match(
        self,
        term: str,
        candidates: list[TerminologyConcept],
    ) -> TerminologyMatch:
        """Find the single best match for a term among candidates."""
        normalized = term.strip().lower()

        # Strategy 1: Exact match on display (Spanish)
        for concept in candidates:
            if concept.display.lower() == normalized:
                return TerminologyMatch(
                    concept=concept,
                    score=EXACT_MATCH_SCORE,
                    match_type=MatchType.EXACT_DISPLAY,
                    query=term,
                )

        # Strategy 2: Exact match on display_en (English)
        for concept in candidates:
            if concept.display_en.lower() == normalized:
                return TerminologyMatch(
                    concept=concept,
                    score=EXACT_MATCH_SCORE,
                    match_type=MatchType.EXACT_DISPLAY,
                    query=term,
                )

        # Strategy 3: Exact match on aliases
        for concept in candidates:
            for alias in concept.aliases:
                if alias.lower() == normalized:
                    return TerminologyMatch(
                        concept=concept,
                        score=EXACT_MATCH_SCORE,
                        match_type=MatchType.EXACT_ALIAS,
                        query=term,
                    )

        # Strategy 4: Fuzzy match
        best_score = 0.0
        best_concept: TerminologyConcept | None = None
        for concept in candidates:
            score = self._fuzzy_score(normalized, concept)
            if score > best_score:
                best_score = score
                best_concept = concept

        if best_concept is not None and best_score >= self._config.low_confidence_threshold:
            return TerminologyMatch(
                concept=best_concept,
                score=best_score,
                match_type=MatchType.FUZZY,
                query=term,
            )

        return TerminologyMatch(
            concept=None,
            score=best_score,
            match_type=MatchType.NO_MATCH,
            query=term,
        )

    def _score_all(
        self,
        term: str,
        candidates: list[TerminologyConcept],
    ) -> list[TerminologyMatch]:
        """Score all candidates against a term."""
        normalized = term.strip().lower()
        results: list[TerminologyMatch] = []
        seen_codes: set[tuple[str, TerminologySystem]] = set()

        for concept in candidates:
            key = (concept.code, concept.system)
            if key in seen_codes:
                continue
            seen_codes.add(key)

            # Check exact matches first
            match_type = MatchType.FUZZY
            score = self._fuzzy_score(normalized, concept)

            if concept.display.lower() == normalized or concept.display_en.lower() == normalized:
                score = EXACT_MATCH_SCORE
                match_type = MatchType.EXACT_DISPLAY
            else:
                for alias in concept.aliases:
                    if alias.lower() == normalized:
                        score = EXACT_MATCH_SCORE
                        match_type = MatchType.EXACT_ALIAS
                        break

            results.append(
                TerminologyMatch(
                    concept=concept,
                    score=score,
                    match_type=match_type,
                    query=term,
                )
            )

        return results

    @staticmethod
    def _fuzzy_score(normalized_term: str, concept: TerminologyConcept) -> float:
        """Compute the best fuzzy score for a term against a concept.

        Uses the maximum of token_sort_ratio across display, display_en,
        and all aliases.
        """
        texts = [concept.display.lower(), concept.display_en.lower()]
        texts.extend(a.lower() for a in concept.aliases)

        best = 0.0
        for text in texts:
            # token_sort_ratio handles word reordering well
            token_score = fuzz.token_sort_ratio(normalized_term, text)
            # partial_ratio handles substring matches (e.g. abbreviations)
            partial_score = fuzz.partial_ratio(normalized_term, text)
            # Weighted combination: favour token_sort but consider partial
            combined = token_score * 0.6 + partial_score * 0.4
            if combined > best:
                best = combined

        return best

    # -- CSV loading --------------------------------------------------------

    def _load_from_locale_pack(self, locale_pack: LocalePack) -> None:
        """Load terminology data from a locale pack's bundled CSVs."""
        for sys_def in locale_pack.terminology_systems:
            system = TerminologySystem(sys_def.system_uri)
            self._load_csv(
                system,
                sys_def.csv_filename,
                data_package=sys_def.data_package,
            )

    def _load_csv(
        self,
        system: TerminologySystem,
        filename: str,
        data_package: str,
    ) -> None:
        """Load a single CSV file for a terminology system."""
        try:
            data_files = resources.files(data_package) / filename
            text = data_files.read_text(encoding="utf-8")
        except Exception as exc:
            raise TerminologyDataError(f"Failed to read {filename}: {exc}") from exc

        reader = csv.DictReader(text.splitlines())
        count = 0
        for row in reader:
            try:
                code = row["code"].strip()
                display = row["display"].strip()
                display_en = row.get("display_en", "").strip()
                raw_aliases = row.get("aliases", "").strip()
                aliases = tuple(a.strip() for a in raw_aliases.split("|") if a.strip())

                concept = TerminologyConcept(
                    code=code,
                    system=system,
                    display=display,
                    display_en=display_en,
                    aliases=aliases,
                )
                self._register_concept(concept)
                count += 1
            except KeyError as exc:
                raise TerminologyDataError(f"Missing required column in {filename}: {exc}") from exc

        logger.debug(
            "terminology_csv_loaded",
            system=system.name,
            filename=filename,
            concepts=count,
        )
