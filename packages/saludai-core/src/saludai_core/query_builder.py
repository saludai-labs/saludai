"""FHIR R4 query builder.

Transforms structured parameters into FHIR search URLs compatible with
``FHIRClient.search()``.  This module is purely synchronous — it performs
no I/O, only data transformation.

Example::

    query = (
        FHIRQueryBuilder("Condition")
        .where("code", snomed("44054006"))
        .where("subject:Patient.birthdate", date_param("le", "1966-01-01"))
        .include("subject")
        .count(50)
        .build()
    )
    params = query.to_params()
    bundle = await client.search(query.resource_type, params)
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field

import structlog

from saludai_core.exceptions import QueryBuilderValidationError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# FHIR terminology system URIs
SNOMED_CT_SYSTEM = "http://snomed.info/sct"
LOINC_SYSTEM = "http://loinc.org"
CIE_10_SYSTEM = "http://hl7.org/fhir/sid/icd-10"

# Valid date formats (ISO 8601 subsets accepted by FHIR)
_DATE_RE = re.compile(
    r"^\d{4}"  # YYYY
    r"(?:-\d{2}"  # -MM
    r"(?:-\d{2}"  # -DD
    r"(?:T\d{2}:\d{2}"  # THH:MM
    r"(?::\d{2})?"  # :SS
    r"(?:\.\d+)?"  # .fractional
    r"(?:Z|[+-]\d{2}:\d{2})?"  # timezone
    r")?)?)?"
    r"$"
)

# Valid _total values per FHIR spec
_VALID_TOTAL_VALUES = frozenset({"none", "estimate", "accurate"})

# Valid _summary values per FHIR spec
_VALID_SUMMARY_VALUES = frozenset({"true", "text", "data", "count", "false"})


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FHIRResourceType(enum.StrEnum):
    """Common FHIR R4 resource types relevant to SaludAI."""

    PATIENT = "Patient"
    CONDITION = "Condition"
    OBSERVATION = "Observation"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION_STATEMENT = "MedicationStatement"
    MEDICATION = "Medication"
    ENCOUNTER = "Encounter"
    PROCEDURE = "Procedure"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    IMMUNIZATION = "Immunization"
    CARE_PLAN = "CarePlan"
    ORGANIZATION = "Organization"
    PRACTITIONER = "Practitioner"
    LOCATION = "Location"


class DatePrefix(enum.StrEnum):
    """FHIR search date comparison prefixes."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GE = "ge"
    LE = "le"
    SA = "sa"
    EB = "eb"


class SummaryMode(enum.StrEnum):
    """FHIR _summary parameter modes."""

    TRUE = "true"
    TEXT = "text"
    DATA = "data"
    COUNT = "count"
    FALSE = "false"


class SortOrder(enum.StrEnum):
    """Sort direction for FHIR _sort parameter."""

    ASC = ""
    DESC = "-"


# ---------------------------------------------------------------------------
# Parameter value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenParam:
    """A FHIR token search parameter (system|code).

    Args:
        system: The code system URI (e.g. ``"http://snomed.info/sct"``).
        code: The code value (e.g. ``"44054006"``).
    """

    system: str
    code: str

    def to_fhir(self) -> str:
        """Serialize to FHIR token format ``system|code``."""
        return f"{self.system}|{self.code}"


@dataclass(frozen=True, slots=True)
class DateParam:
    """A FHIR date search parameter with comparison prefix.

    Args:
        prefix: Comparison prefix (eq, ne, gt, lt, ge, le, sa, eb).
        value: ISO 8601 date string (YYYY, YYYY-MM, YYYY-MM-DD, or datetime).
    """

    prefix: DatePrefix
    value: str

    def __post_init__(self) -> None:
        if not _DATE_RE.match(self.value):
            raise QueryBuilderValidationError(
                f"Invalid date format: {self.value!r}. "
                "Expected ISO 8601 (YYYY, YYYY-MM, YYYY-MM-DD, or datetime)."
            )

    def to_fhir(self) -> str:
        """Serialize to FHIR date format ``prefixvalue``."""
        return f"{self.prefix}{self.value}"


@dataclass(frozen=True, slots=True)
class ReferenceParam:
    """A FHIR reference search parameter (ResourceType/id).

    Args:
        resource_type: Referenced resource type (e.g. ``"Patient"``).
        resource_id: Logical id of the referenced resource.
    """

    resource_type: str
    resource_id: str

    def to_fhir(self) -> str:
        """Serialize to FHIR reference format ``ResourceType/id``."""
        return f"{self.resource_type}/{self.resource_id}"


@dataclass(frozen=True, slots=True)
class QuantityParam:
    """A FHIR quantity search parameter.

    Args:
        prefix: Comparison prefix.
        value: Numeric value.
        system: Optional unit system URI.
        code: Optional unit code.
    """

    prefix: DatePrefix
    value: float
    system: str = ""
    code: str = ""

    def to_fhir(self) -> str:
        """Serialize to FHIR quantity format ``prefixvalue|system|code``."""
        prefix_str = self.prefix.value
        if self.system or self.code:
            return f"{prefix_str}{self.value}|{self.system}|{self.code}"
        return f"{prefix_str}{self.value}"


@dataclass(frozen=True, slots=True)
class StringParam:
    """A FHIR string search parameter.

    Args:
        value: The search string.
        exact: If ``True``, use ``:exact`` modifier on the parameter name.
    """

    value: str
    exact: bool = False

    def to_fhir(self) -> str:
        """Serialize to FHIR string format (the value itself)."""
        return self.value


# Union of all parameter value types
ParamValue = TokenParam | DateParam | ReferenceParam | QuantityParam | StringParam


@dataclass(frozen=True, slots=True)
class IncludeParam:
    """A FHIR _include or _revinclude parameter.

    Args:
        source_type: The source resource type (e.g. ``"Condition"``).
        search_param: The search parameter to follow (e.g. ``"subject"``).
        target_type: Optional target resource type filter.
        reverse: If ``True``, generates ``_revinclude`` instead of ``_include``.
    """

    source_type: str
    search_param: str
    target_type: str = ""
    reverse: bool = False

    def to_fhir(self) -> str:
        """Serialize to FHIR include format ``SourceType:param[:TargetType]``."""
        result = f"{self.source_type}:{self.search_param}"
        if self.target_type:
            result = f"{result}:{self.target_type}"
        return result

    @property
    def param_name(self) -> str:
        """Return the FHIR parameter name (``_include`` or ``_revinclude``)."""
        return "_revinclude" if self.reverse else "_include"


@dataclass(frozen=True, slots=True)
class SortParam:
    """A FHIR _sort parameter.

    Args:
        field: The field to sort by (e.g. ``"birthdate"``).
        order: Sort direction (ASC or DESC).
    """

    field: str
    order: SortOrder = SortOrder.ASC

    def to_fhir(self) -> str:
        """Serialize to FHIR sort format (``field`` or ``-field``)."""
        return f"{self.order}{self.field}"


# ---------------------------------------------------------------------------
# FHIRQuery — the built output
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FHIRQuery:
    """An immutable, validated FHIR search query.

    This is the output of ``FHIRQueryBuilder.build()``.  Use ``to_params()``
    to obtain a dict compatible with ``FHIRClient.search()``.
    """

    resource_type: str
    params: tuple[tuple[str, str], ...] = ()

    def to_params(self) -> dict[str, str | list[str]]:
        """Convert to a dict suitable for ``FHIRClient.search()``.

        Repeated keys (e.g. multiple ``_include``) are collected into lists.
        """
        result: dict[str, str | list[str]] = {}
        for key, value in self.params:
            if key in result:
                existing = result[key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    result[key] = [existing, value]
            else:
                result[key] = value
        return result


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def token(system: str, code: str) -> TokenParam:
    """Create a generic token parameter."""
    return TokenParam(system=system, code=code)


def snomed(code: str) -> TokenParam:
    """Create a SNOMED CT token parameter."""
    return TokenParam(system=SNOMED_CT_SYSTEM, code=code)


def loinc(code: str) -> TokenParam:
    """Create a LOINC token parameter."""
    return TokenParam(system=LOINC_SYSTEM, code=code)


def cie10(code: str) -> TokenParam:
    """Create a CIE-10 token parameter."""
    return TokenParam(system=CIE_10_SYSTEM, code=code)


def date_param(prefix: str | DatePrefix, value: str) -> DateParam:
    """Create a date parameter with validation.

    Args:
        prefix: Comparison prefix (e.g. ``"ge"``, ``"le"``).
        value: ISO 8601 date string.

    Returns:
        A validated ``DateParam``.
    """
    return DateParam(prefix=DatePrefix(prefix), value=value)


def reference(resource_type: str, resource_id: str) -> ReferenceParam:
    """Create a reference parameter."""
    return ReferenceParam(resource_type=resource_type, resource_id=resource_id)


def quantity(
    prefix: str | DatePrefix,
    value: float,
    system: str = "",
    code: str = "",
) -> QuantityParam:
    """Create a quantity parameter."""
    return QuantityParam(prefix=DatePrefix(prefix), value=value, system=system, code=code)


# ---------------------------------------------------------------------------
# FHIRQueryBuilder — fluent API
# ---------------------------------------------------------------------------


@dataclass
class FHIRQueryBuilder:
    """Fluent builder for constructing FHIR search queries.

    Args:
        resource_type: The FHIR resource type to search (e.g. ``"Patient"``).
        validate: If ``True`` (default), validate the resource type against
            ``FHIRResourceType``.  Set to ``False`` for custom resource types.

    Example::

        query = (
            FHIRQueryBuilder("Condition")
            .where("code", snomed("44054006"))
            .include("subject")
            .count(50)
            .build()
        )
    """

    _resource_type: str
    _validate: bool = True
    _params: list[tuple[str, str]] = field(default_factory=list, init=False, repr=False)

    def __init__(self, resource_type: str, *, validate: bool = True) -> None:
        self._resource_type = resource_type
        self._validate = validate
        self._params = []

        if validate:
            self._validate_resource_type(resource_type)

    # -- Parameter methods --------------------------------------------------

    def where(self, param_name: str, value: ParamValue) -> FHIRQueryBuilder:
        """Add a search parameter.

        Args:
            param_name: FHIR search parameter name (e.g. ``"code"``,
                ``"subject:Patient.birthdate"``).
            value: A parameter value object with a ``to_fhir()`` method.

        Returns:
            Self for chaining.
        """
        if not param_name:
            raise QueryBuilderValidationError("Parameter name cannot be empty")

        key = param_name
        if isinstance(value, StringParam) and value.exact:
            key = f"{param_name}:exact"

        self._params.append((key, value.to_fhir()))
        return self

    def where_token(
        self,
        param_name: str,
        system: str,
        code: str,
    ) -> FHIRQueryBuilder:
        """Add a token search parameter (convenience wrapper).

        Args:
            param_name: FHIR search parameter name.
            system: Code system URI.
            code: Code value.

        Returns:
            Self for chaining.
        """
        return self.where(param_name, TokenParam(system=system, code=code))

    def where_date(
        self,
        param_name: str,
        prefix: str | DatePrefix,
        value: str,
    ) -> FHIRQueryBuilder:
        """Add a date search parameter (convenience wrapper).

        Args:
            param_name: FHIR search parameter name.
            prefix: Comparison prefix.
            value: ISO 8601 date string.

        Returns:
            Self for chaining.
        """
        return self.where(param_name, date_param(prefix, value))

    def where_reference(
        self,
        param_name: str,
        resource_type: str,
        resource_id: str,
    ) -> FHIRQueryBuilder:
        """Add a reference search parameter (convenience wrapper).

        Args:
            param_name: FHIR search parameter name.
            resource_type: Referenced resource type.
            resource_id: Referenced resource id.

        Returns:
            Self for chaining.
        """
        ref = ReferenceParam(resource_type=resource_type, resource_id=resource_id)
        return self.where(param_name, ref)

    def where_string(
        self,
        param_name: str,
        value: str,
        *,
        exact: bool = False,
    ) -> FHIRQueryBuilder:
        """Add a string search parameter (convenience wrapper).

        Args:
            param_name: FHIR search parameter name.
            value: The search string.
            exact: If ``True``, use ``:exact`` modifier.

        Returns:
            Self for chaining.
        """
        return self.where(param_name, StringParam(value=value, exact=exact))

    # -- Include / revinclude -----------------------------------------------

    def include(
        self,
        search_param: str,
        *,
        target_type: str = "",
    ) -> FHIRQueryBuilder:
        """Add an ``_include`` parameter.

        The source type is inferred from the builder's resource type.

        Args:
            search_param: The search parameter to follow (e.g. ``"subject"``).
            target_type: Optional target resource type filter.

        Returns:
            Self for chaining.
        """
        inc = IncludeParam(
            source_type=self._resource_type,
            search_param=search_param,
            target_type=target_type,
        )
        self._params.append((inc.param_name, inc.to_fhir()))
        return self

    def revinclude(
        self,
        source_type: str,
        search_param: str,
        *,
        target_type: str = "",
    ) -> FHIRQueryBuilder:
        """Add a ``_revinclude`` parameter.

        Args:
            source_type: The source resource type for the reverse include.
            search_param: The search parameter to follow.
            target_type: Optional target resource type filter.

        Returns:
            Self for chaining.
        """
        inc = IncludeParam(
            source_type=source_type,
            search_param=search_param,
            target_type=target_type,
            reverse=True,
        )
        self._params.append((inc.param_name, inc.to_fhir()))
        return self

    # -- Sort, count, total, elements ---------------------------------------

    def sort(self, field_name: str, order: SortOrder = SortOrder.ASC) -> FHIRQueryBuilder:
        """Add a ``_sort`` parameter.

        Args:
            field_name: The field to sort by.
            order: Sort direction.

        Returns:
            Self for chaining.
        """
        sp = SortParam(field=field_name, order=order)
        self._params.append(("_sort", sp.to_fhir()))
        return self

    def count(self, value: int) -> FHIRQueryBuilder:
        """Set the ``_count`` parameter (page size).

        Args:
            value: Maximum number of results per page.  Must be positive.

        Returns:
            Self for chaining.
        """
        if value <= 0:
            raise QueryBuilderValidationError(f"_count must be positive, got {value}")
        self._params.append(("_count", str(value)))
        return self

    def total(self, mode: str) -> FHIRQueryBuilder:
        """Set the ``_total`` parameter.

        Args:
            mode: One of ``"none"``, ``"estimate"``, or ``"accurate"``.

        Returns:
            Self for chaining.
        """
        if mode not in _VALID_TOTAL_VALUES:
            raise QueryBuilderValidationError(
                f"_total must be one of {sorted(_VALID_TOTAL_VALUES)}, got {mode!r}"
            )
        self._params.append(("_total", mode))
        return self

    def elements(self, *fields: str) -> FHIRQueryBuilder:
        """Set the ``_elements`` parameter to request specific fields only.

        Args:
            fields: Field names to include in the response.

        Returns:
            Self for chaining.
        """
        if not fields:
            raise QueryBuilderValidationError("_elements requires at least one field")
        self._params.append(("_elements", ",".join(fields)))
        return self

    def summary(self, mode: str | SummaryMode) -> FHIRQueryBuilder:
        """Set the ``_summary`` parameter.

        Args:
            mode: One of ``"true"``, ``"text"``, ``"data"``, ``"count"``,
                or ``"false"``.  Can also be a ``SummaryMode`` enum value.

        Returns:
            Self for chaining.
        """
        mode_str = str(mode)
        if mode_str not in _VALID_SUMMARY_VALUES:
            raise QueryBuilderValidationError(
                f"_summary must be one of {sorted(_VALID_SUMMARY_VALUES)}, got {mode_str!r}"
            )
        self._params.append(("_summary", mode_str))
        return self

    # -- Build --------------------------------------------------------------

    def build(self) -> FHIRQuery:
        """Build an immutable ``FHIRQuery`` from the current state.

        Returns:
            A frozen ``FHIRQuery`` ready for use with ``FHIRClient.search()``.
        """
        query = FHIRQuery(
            resource_type=self._resource_type,
            params=tuple(self._params),
        )
        logger.debug(
            "query_built",
            resource_type=self._resource_type,
            param_count=len(self._params),
        )
        return query

    # -- Validation ---------------------------------------------------------

    @staticmethod
    def _validate_resource_type(resource_type: str) -> None:
        """Validate that resource_type is a known FHIR resource type."""
        valid_types = {member.value for member in FHIRResourceType}
        if resource_type not in valid_types:
            raise QueryBuilderValidationError(
                f"Unknown resource type: {resource_type!r}. "
                f"Use validate=False for custom resource types."
            )
