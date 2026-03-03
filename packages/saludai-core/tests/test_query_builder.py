"""Tests for the FHIR Query Builder module."""

from __future__ import annotations

import pytest

from saludai_core.exceptions import QueryBuilderError, QueryBuilderValidationError
from saludai_core.query_builder import (
    CIE_10_SYSTEM,
    LOINC_SYSTEM,
    SNOMED_CT_SYSTEM,
    DatePrefix,
    FHIRQuery,
    FHIRQueryBuilder,
    FHIRResourceType,
    IncludeParam,
    SortOrder,
    SortParam,
    StringParam,
    TokenParam,
    cie10,
    date_param,
    loinc,
    quantity,
    reference,
    snomed,
    token,
)

# ---------------------------------------------------------------------------
# 1. TestFHIRResourceType
# ---------------------------------------------------------------------------


class TestFHIRResourceType:
    """Tests for FHIRResourceType enum."""

    def test_patient_value(self) -> None:
        assert FHIRResourceType.PATIENT == "Patient"

    def test_condition_value(self) -> None:
        assert FHIRResourceType.CONDITION == "Condition"

    def test_observation_value(self) -> None:
        assert FHIRResourceType.OBSERVATION == "Observation"

    def test_medication_request_value(self) -> None:
        assert FHIRResourceType.MEDICATION_REQUEST == "MedicationRequest"

    def test_str_coercion(self) -> None:
        assert str(FHIRResourceType.PATIENT) == "Patient"

    def test_resource_type_is_string(self) -> None:
        assert isinstance(FHIRResourceType.PATIENT, str)

    def test_all_types_exist(self) -> None:
        expected = {
            "Patient",
            "Condition",
            "Observation",
            "MedicationRequest",
            "MedicationStatement",
            "Medication",
            "Encounter",
            "Procedure",
            "DiagnosticReport",
            "AllergyIntolerance",
            "Immunization",
            "CarePlan",
            "Organization",
            "Practitioner",
            "Location",
        }
        actual = {member.value for member in FHIRResourceType}
        assert actual == expected


# ---------------------------------------------------------------------------
# 2. TestTokenParam
# ---------------------------------------------------------------------------


class TestTokenParam:
    """Tests for TokenParam and token factory shortcuts."""

    def test_to_fhir(self) -> None:
        tp = TokenParam(system="http://example.org", code="123")
        assert tp.to_fhir() == "http://example.org|123"

    def test_frozen(self) -> None:
        tp = TokenParam(system="http://example.org", code="123")
        with pytest.raises(AttributeError):
            tp.code = "456"  # type: ignore[misc]

    def test_snomed_shortcut(self) -> None:
        tp = snomed("44054006")
        assert tp.system == SNOMED_CT_SYSTEM
        assert tp.code == "44054006"
        assert tp.to_fhir() == f"{SNOMED_CT_SYSTEM}|44054006"

    def test_loinc_shortcut(self) -> None:
        tp = loinc("2339-0")
        assert tp.system == LOINC_SYSTEM
        assert tp.code == "2339-0"

    def test_cie10_shortcut(self) -> None:
        tp = cie10("E11")
        assert tp.system == CIE_10_SYSTEM
        assert tp.code == "E11"

    def test_generic_token(self) -> None:
        tp = token("http://custom.org", "ABC")
        assert tp.to_fhir() == "http://custom.org|ABC"


# ---------------------------------------------------------------------------
# 3. TestDateParam
# ---------------------------------------------------------------------------


class TestDateParam:
    """Tests for DateParam and date_param factory."""

    def test_year_only(self) -> None:
        dp = date_param("ge", "1960")
        assert dp.to_fhir() == "ge1960"

    def test_year_month(self) -> None:
        dp = date_param("le", "1966-01")
        assert dp.to_fhir() == "le1966-01"

    def test_full_date(self) -> None:
        dp = date_param("eq", "2024-03-15")
        assert dp.to_fhir() == "eq2024-03-15"

    def test_datetime_with_timezone(self) -> None:
        dp = date_param("gt", "2024-01-01T00:00:00Z")
        assert dp.to_fhir() == "gt2024-01-01T00:00:00Z"

    def test_datetime_with_offset(self) -> None:
        dp = date_param("lt", "2024-01-01T12:30:00-03:00")
        assert dp.to_fhir() == "lt2024-01-01T12:30:00-03:00"

    def test_all_prefixes(self) -> None:
        for prefix in DatePrefix:
            dp = date_param(prefix, "2024-01-01")
            assert dp.to_fhir().startswith(prefix.value)

    def test_invalid_date_format(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="Invalid date format"):
            date_param("ge", "not-a-date")

    def test_invalid_date_day_only(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="Invalid date format"):
            date_param("ge", "15")

    def test_frozen(self) -> None:
        dp = date_param("ge", "2024-01-01")
        with pytest.raises(AttributeError):
            dp.value = "2025-01-01"  # type: ignore[misc]

    def test_prefix_enum_from_string(self) -> None:
        dp = date_param("sa", "2024-06-01")
        assert dp.prefix == DatePrefix.SA


# ---------------------------------------------------------------------------
# 4. TestReferenceParam
# ---------------------------------------------------------------------------


class TestReferenceParam:
    """Tests for ReferenceParam and reference factory."""

    def test_to_fhir(self) -> None:
        rp = reference("Patient", "123")
        assert rp.to_fhir() == "Patient/123"

    def test_frozen(self) -> None:
        rp = reference("Patient", "123")
        with pytest.raises(AttributeError):
            rp.resource_id = "456"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. TestQuantityParam
# ---------------------------------------------------------------------------


class TestQuantityParam:
    """Tests for QuantityParam and quantity factory."""

    def test_without_units(self) -> None:
        qp = quantity("gt", 5.5)
        assert qp.to_fhir() == "gt5.5"

    def test_with_units(self) -> None:
        qp = quantity("gt", 5.5, system="http://unitsofmeasure.org", code="mg")
        assert qp.to_fhir() == "gt5.5|http://unitsofmeasure.org|mg"

    def test_integer_value(self) -> None:
        qp = quantity("le", 100.0)
        assert qp.to_fhir() == "le100.0"

    def test_frozen(self) -> None:
        qp = quantity("eq", 1.0)
        with pytest.raises(AttributeError):
            qp.value = 2.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. TestStringParam
# ---------------------------------------------------------------------------


class TestStringParam:
    """Tests for StringParam."""

    def test_basic(self) -> None:
        sp = StringParam(value="Garcia")
        assert sp.to_fhir() == "Garcia"
        assert sp.exact is False

    def test_exact(self) -> None:
        sp = StringParam(value="Garcia", exact=True)
        assert sp.to_fhir() == "Garcia"
        assert sp.exact is True

    def test_frozen(self) -> None:
        sp = StringParam(value="test")
        with pytest.raises(AttributeError):
            sp.value = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 7. TestIncludeParam
# ---------------------------------------------------------------------------


class TestIncludeParam:
    """Tests for IncludeParam."""

    def test_basic_include(self) -> None:
        inc = IncludeParam(source_type="Condition", search_param="subject")
        assert inc.to_fhir() == "Condition:subject"
        assert inc.param_name == "_include"

    def test_include_with_target(self) -> None:
        inc = IncludeParam(
            source_type="Condition",
            search_param="subject",
            target_type="Patient",
        )
        assert inc.to_fhir() == "Condition:subject:Patient"

    def test_revinclude(self) -> None:
        inc = IncludeParam(
            source_type="Condition",
            search_param="subject",
            reverse=True,
        )
        assert inc.to_fhir() == "Condition:subject"
        assert inc.param_name == "_revinclude"


# ---------------------------------------------------------------------------
# 8. TestSortParam
# ---------------------------------------------------------------------------


class TestSortParam:
    """Tests for SortParam."""

    def test_ascending(self) -> None:
        sp = SortParam(field="birthdate")
        assert sp.to_fhir() == "birthdate"

    def test_descending(self) -> None:
        sp = SortParam(field="birthdate", order=SortOrder.DESC)
        assert sp.to_fhir() == "-birthdate"

    def test_default_is_ascending(self) -> None:
        sp = SortParam(field="date")
        assert sp.order == SortOrder.ASC


# ---------------------------------------------------------------------------
# 9. TestFHIRQueryBuilder
# ---------------------------------------------------------------------------


class TestFHIRQueryBuilder:
    """Tests for the FHIRQueryBuilder fluent API."""

    def test_minimal_build(self) -> None:
        query = FHIRQueryBuilder("Patient").build()
        assert query.resource_type == "Patient"
        assert query.params == ()

    def test_where_token(self) -> None:
        query = FHIRQueryBuilder("Condition").where("code", snomed("44054006")).build()
        params = query.to_params()
        assert params["code"] == f"{SNOMED_CT_SYSTEM}|44054006"

    def test_where_token_convenience(self) -> None:
        query = (
            FHIRQueryBuilder("Condition").where_token("code", SNOMED_CT_SYSTEM, "44054006").build()
        )
        params = query.to_params()
        assert params["code"] == f"{SNOMED_CT_SYSTEM}|44054006"

    def test_where_date_convenience(self) -> None:
        query = FHIRQueryBuilder("Patient").where_date("birthdate", "le", "1966-01-01").build()
        params = query.to_params()
        assert params["birthdate"] == "le1966-01-01"

    def test_where_reference_convenience(self) -> None:
        query = FHIRQueryBuilder("Observation").where_reference("subject", "Patient", "123").build()
        params = query.to_params()
        assert params["subject"] == "Patient/123"

    def test_where_string_convenience(self) -> None:
        query = FHIRQueryBuilder("Patient").where_string("family", "Garcia").build()
        params = query.to_params()
        assert params["family"] == "Garcia"

    def test_where_string_exact(self) -> None:
        query = FHIRQueryBuilder("Patient").where_string("family", "Garcia", exact=True).build()
        params = query.to_params()
        assert params["family:exact"] == "Garcia"

    def test_include(self) -> None:
        query = FHIRQueryBuilder("Condition").include("subject").build()
        params = query.to_params()
        assert params["_include"] == "Condition:subject"

    def test_revinclude(self) -> None:
        query = FHIRQueryBuilder("Patient").revinclude("Condition", "subject").build()
        params = query.to_params()
        assert params["_revinclude"] == "Condition:subject"

    def test_sort_ascending(self) -> None:
        query = FHIRQueryBuilder("Patient").sort("birthdate").build()
        params = query.to_params()
        assert params["_sort"] == "birthdate"

    def test_sort_descending(self) -> None:
        query = FHIRQueryBuilder("Patient").sort("birthdate", SortOrder.DESC).build()
        params = query.to_params()
        assert params["_sort"] == "-birthdate"

    def test_count(self) -> None:
        query = FHIRQueryBuilder("Patient").count(50).build()
        params = query.to_params()
        assert params["_count"] == "50"

    def test_count_zero_raises(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="_count must be positive"):
            FHIRQueryBuilder("Patient").count(0)

    def test_count_negative_raises(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="_count must be positive"):
            FHIRQueryBuilder("Patient").count(-1)

    def test_total(self) -> None:
        query = FHIRQueryBuilder("Patient").total("accurate").build()
        params = query.to_params()
        assert params["_total"] == "accurate"

    def test_total_invalid_raises(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="_total must be one of"):
            FHIRQueryBuilder("Patient").total("invalid")

    def test_elements(self) -> None:
        query = FHIRQueryBuilder("Patient").elements("id", "name", "birthDate").build()
        params = query.to_params()
        assert params["_elements"] == "id,name,birthDate"

    def test_elements_empty_raises(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="_elements requires"):
            FHIRQueryBuilder("Patient").elements()

    def test_invalid_resource_type_raises(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="Unknown resource type"):
            FHIRQueryBuilder("InvalidType")

    def test_validate_false_allows_custom_type(self) -> None:
        query = FHIRQueryBuilder("CustomResource", validate=False).build()
        assert query.resource_type == "CustomResource"

    def test_empty_param_name_raises(self) -> None:
        with pytest.raises(QueryBuilderValidationError, match="Parameter name cannot be empty"):
            FHIRQueryBuilder("Patient").where("", StringParam(value="test"))

    def test_chaining(self) -> None:
        builder = FHIRQueryBuilder("Condition")
        result = builder.where("code", snomed("44054006"))
        assert result is builder


# ---------------------------------------------------------------------------
# 10. TestFHIRQueryToParams
# ---------------------------------------------------------------------------


class TestFHIRQueryToParams:
    """Tests for FHIRQuery.to_params() serialization."""

    def test_empty_params(self) -> None:
        query = FHIRQuery(resource_type="Patient")
        assert query.to_params() == {}

    def test_single_param(self) -> None:
        query = FHIRQuery(
            resource_type="Patient",
            params=(("name", "Garcia"),),
        )
        assert query.to_params() == {"name": "Garcia"}

    def test_multiple_different_params(self) -> None:
        query = FHIRQuery(
            resource_type="Patient",
            params=(("name", "Garcia"), ("birthdate", "ge1960-01-01")),
        )
        result = query.to_params()
        assert result["name"] == "Garcia"
        assert result["birthdate"] == "ge1960-01-01"

    def test_repeated_params_become_list(self) -> None:
        query = FHIRQuery(
            resource_type="Condition",
            params=(
                ("_include", "Condition:subject"),
                ("_include", "Condition:encounter"),
            ),
        )
        result = query.to_params()
        assert result["_include"] == ["Condition:subject", "Condition:encounter"]

    def test_three_repeated_params(self) -> None:
        query = FHIRQuery(
            resource_type="Patient",
            params=(
                ("_revinclude", "Condition:subject"),
                ("_revinclude", "Observation:subject"),
                ("_revinclude", "MedicationRequest:subject"),
            ),
        )
        result = query.to_params()
        assert result["_revinclude"] == [
            "Condition:subject",
            "Observation:subject",
            "MedicationRequest:subject",
        ]

    def test_frozen_query(self) -> None:
        query = FHIRQuery(resource_type="Patient", params=(("name", "Garcia"),))
        with pytest.raises(AttributeError):
            query.resource_type = "Condition"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 11. TestChainedParams
# ---------------------------------------------------------------------------


class TestChainedParams:
    """Tests for chained FHIR search parameters."""

    def test_chained_date(self) -> None:
        query = (
            FHIRQueryBuilder("Condition")
            .where("subject:Patient.birthdate", date_param("le", "1966-01-01"))
            .build()
        )
        params = query.to_params()
        assert params["subject:Patient.birthdate"] == "le1966-01-01"

    def test_chained_string(self) -> None:
        query = (
            FHIRQueryBuilder("Condition")
            .where("subject:Patient.name", StringParam(value="Garcia"))
            .build()
        )
        params = query.to_params()
        assert params["subject:Patient.name"] == "Garcia"

    def test_chained_address(self) -> None:
        query = (
            FHIRQueryBuilder("Condition")
            .where("subject:Patient.address-state", StringParam(value="Buenos Aires"))
            .build()
        )
        params = query.to_params()
        assert params["subject:Patient.address-state"] == "Buenos Aires"


# ---------------------------------------------------------------------------
# 12. TestGolden — real clinical queries
# ---------------------------------------------------------------------------


class TestGolden:
    """Golden tests for realistic clinical FHIR queries."""

    def test_diabetes_tipo_2_mayores_60(self) -> None:
        """Pacientes con diabetes tipo 2 mayores de 60."""
        query = (
            FHIRQueryBuilder("Condition")
            .where("code", snomed("44054006"))
            .where("subject:Patient.birthdate", date_param("le", "1966-01-01"))
            .include("subject")
            .count(50)
            .build()
        )
        params = query.to_params()
        assert params == {
            "code": f"{SNOMED_CT_SYSTEM}|44054006",
            "subject:Patient.birthdate": "le1966-01-01",
            "_include": "Condition:subject",
            "_count": "50",
        }

    def test_resultados_laboratorio_glucosa(self) -> None:
        """Resultados de laboratorio de glucosa."""
        query = (
            FHIRQueryBuilder("Observation")
            .where("code", loinc("2339-0"))
            .sort("date", SortOrder.DESC)
            .count(20)
            .build()
        )
        params = query.to_params()
        assert params == {
            "code": f"{LOINC_SYSTEM}|2339-0",
            "_sort": "-date",
            "_count": "20",
        }

    def test_pacientes_buenos_aires(self) -> None:
        """Pacientes en Buenos Aires."""
        query = (
            FHIRQueryBuilder("Patient")
            .where_string("address-state", "Buenos Aires")
            .total("accurate")
            .build()
        )
        params = query.to_params()
        assert params == {
            "address-state": "Buenos Aires",
            "_total": "accurate",
        }

    def test_medicaciones_activas(self) -> None:
        """Medicaciones activas."""
        query = (
            FHIRQueryBuilder("MedicationRequest")
            .where("status", TokenParam(system="", code="active"))
            .include("subject")
            .include("medication")
            .sort("authoredon", SortOrder.DESC)
            .build()
        )
        params = query.to_params()
        assert params["status"] == "|active"
        assert params["_include"] == [
            "MedicationRequest:subject",
            "MedicationRequest:medication",
        ]
        assert params["_sort"] == "-authoredon"

    def test_condiciones_por_cie10(self) -> None:
        """Condiciones por código CIE-10."""
        query = FHIRQueryBuilder("Condition").where("code", cie10("E11")).include("subject").build()
        params = query.to_params()
        assert params == {
            "code": f"{CIE_10_SYSTEM}|E11",
            "_include": "Condition:subject",
        }

    def test_patient_with_revinclude(self) -> None:
        """Paciente con sus condiciones y observaciones incluidas."""
        query = (
            FHIRQueryBuilder("Patient")
            .where_string("family", "Garcia", exact=True)
            .revinclude("Condition", "subject")
            .revinclude("Observation", "subject")
            .build()
        )
        params = query.to_params()
        assert params["family:exact"] == "Garcia"
        assert params["_revinclude"] == [
            "Condition:subject",
            "Observation:subject",
        ]

    def test_observations_with_quantity(self) -> None:
        """Observaciones con valor mayor a umbral."""
        query = (
            FHIRQueryBuilder("Observation")
            .where("code", loinc("2339-0"))
            .where("value-quantity", quantity("gt", 126.0, "http://unitsofmeasure.org", "mg/dL"))
            .build()
        )
        params = query.to_params()
        assert params["code"] == f"{LOINC_SYSTEM}|2339-0"
        assert params["value-quantity"] == "gt126.0|http://unitsofmeasure.org|mg/dL"


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Tests for QueryBuilder exception hierarchy."""

    def test_query_builder_error_is_saludai_error(self) -> None:
        from saludai_core.exceptions import SaludAIError

        assert issubclass(QueryBuilderError, SaludAIError)

    def test_validation_error_is_query_builder_error(self) -> None:
        assert issubclass(QueryBuilderValidationError, QueryBuilderError)
