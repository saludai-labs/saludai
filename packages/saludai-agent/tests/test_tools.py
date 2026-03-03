"""Tests for saludai_agent.tools — tool definitions, executors, and registry."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from saludai_agent.exceptions import ToolExecutionError
from saludai_agent.tools import (
    RESOLVE_TERMINOLOGY_DEFINITION,
    SEARCH_FHIR_DEFINITION,
    ToolRegistry,
    execute_resolve_terminology,
    execute_search_fhir,
    format_bundle_summary,
)
from saludai_agent.types import ToolCall

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    """Tool definitions have correct JSON schema structure."""

    def test_resolve_terminology_name(self) -> None:
        assert RESOLVE_TERMINOLOGY_DEFINITION["name"] == "resolve_terminology"

    def test_resolve_terminology_has_description(self) -> None:
        assert len(RESOLVE_TERMINOLOGY_DEFINITION["description"]) > 10

    def test_resolve_terminology_required_fields(self) -> None:
        schema = RESOLVE_TERMINOLOGY_DEFINITION["input_schema"]
        assert "term" in schema["properties"]
        assert "term" in schema["required"]

    def test_resolve_terminology_system_enum(self) -> None:
        schema = RESOLVE_TERMINOLOGY_DEFINITION["input_schema"]
        system_prop = schema["properties"]["system"]
        assert set(system_prop["enum"]) == {"snomed_ct", "cie_10", "loinc"}

    def test_search_fhir_name(self) -> None:
        assert SEARCH_FHIR_DEFINITION["name"] == "search_fhir"

    def test_search_fhir_has_description(self) -> None:
        assert len(SEARCH_FHIR_DEFINITION["description"]) > 10

    def test_search_fhir_required_fields(self) -> None:
        schema = SEARCH_FHIR_DEFINITION["input_schema"]
        assert "resource_type" in schema["properties"]
        assert "resource_type" in schema["required"]

    def test_search_fhir_params_property(self) -> None:
        schema = SEARCH_FHIR_DEFINITION["input_schema"]
        assert "params" in schema["properties"]
        assert schema["properties"]["params"]["type"] == "object"


# ---------------------------------------------------------------------------
# execute_resolve_terminology
# ---------------------------------------------------------------------------


def _make_mock_resolver(
    *,
    code: str = "44054006",
    system_value: str = "http://snomed.info/sct",
    display: str = "Diabetes mellitus tipo 2",
    score: float = 100.0,
    match_type: str = "exact_display",
    is_confident: bool = True,
) -> MagicMock:
    """Create a mock TerminologyResolver with a scripted resolve() result."""
    concept = MagicMock()
    concept.code = code
    concept.system = MagicMock()
    concept.system.value = system_value
    concept.display = display

    match = MagicMock()
    match.concept = concept
    match.score = score
    match.match_type = MagicMock()
    match.match_type.value = match_type
    match.query = "diabetes tipo 2"
    match.is_confident = is_confident

    resolver = MagicMock()
    resolver.resolve.return_value = match
    return resolver


def _make_no_match_resolver() -> MagicMock:
    """Create a mock resolver that returns NO_MATCH."""
    match = MagicMock()
    match.concept = None
    match.score = 30.0
    match.match_type = MagicMock()
    match.match_type.value = "no_match"
    match.query = "unknown term"
    match.is_confident = False

    resolver = MagicMock()
    resolver.resolve.return_value = match
    return resolver


class TestExecuteResolveTerminology:
    """execute_resolve_terminology converts resolver results to JSON."""

    def test_successful_resolution(self) -> None:
        resolver = _make_mock_resolver()
        result = execute_resolve_terminology(resolver, {"term": "diabetes tipo 2"})
        data = json.loads(result)
        assert data["code"] == "44054006"
        assert data["system"] == "http://snomed.info/sct"
        assert data["display"] == "Diabetes mellitus tipo 2"
        assert data["is_confident"] is True
        assert data["score"] == 100.0

    def test_no_match(self) -> None:
        resolver = _make_no_match_resolver()
        result = execute_resolve_terminology(resolver, {"term": "unknown"})
        data = json.loads(result)
        assert data["code"] is None
        assert data["system"] is None
        assert data["display"] is None
        assert data["is_confident"] is False

    def test_with_system_filter(self) -> None:
        resolver = _make_mock_resolver()
        execute_resolve_terminology(resolver, {"term": "diabetes", "system": "snomed_ct"})
        call_args = resolver.resolve.call_args
        # system kwarg should be the TerminologySystem enum
        assert call_args.kwargs.get("system") is not None

    def test_with_cie10_system(self) -> None:
        resolver = _make_mock_resolver()
        execute_resolve_terminology(resolver, {"term": "diabetes", "system": "cie_10"})
        call_args = resolver.resolve.call_args
        assert call_args.kwargs.get("system") is not None

    def test_with_loinc_system(self) -> None:
        resolver = _make_mock_resolver()
        execute_resolve_terminology(resolver, {"term": "glucose", "system": "loinc"})
        call_args = resolver.resolve.call_args
        assert call_args.kwargs.get("system") is not None

    def test_with_no_system(self) -> None:
        resolver = _make_mock_resolver()
        execute_resolve_terminology(resolver, {"term": "test"})
        call_args = resolver.resolve.call_args
        assert call_args.kwargs.get("system") is None

    def test_with_invalid_system(self) -> None:
        resolver = _make_mock_resolver()
        execute_resolve_terminology(resolver, {"term": "test", "system": "invalid"})
        call_args = resolver.resolve.call_args
        assert call_args.kwargs.get("system") is None


# ---------------------------------------------------------------------------
# execute_search_fhir
# ---------------------------------------------------------------------------


def _make_mock_fhir_client(bundle: Any = None) -> MagicMock:
    """Create a mock FHIRClient."""
    client = MagicMock()
    client.search = AsyncMock(return_value=bundle or _make_empty_bundle())
    return client


def _make_empty_bundle() -> MagicMock:
    """Create an empty FHIR Bundle mock."""
    bundle = MagicMock()
    bundle.entry = None
    bundle.total = 0
    return bundle


def _make_bundle_with_patients(count: int = 2) -> MagicMock:
    """Create a FHIR Bundle mock with Patient resources."""
    entries = []
    for i in range(count):
        resource = MagicMock()
        resource.get_resource_type.return_value = "Patient"
        resource.id = f"patient-{i}"
        name_mock = MagicMock()
        name_mock.family = "García"
        name_mock.given = ["Juan"]
        resource.name = [name_mock]
        resource.gender = "male"
        resource.birthDate = "1960-01-15"
        resource.address = []
        resource.code = None
        resource.medicationCodeableConcept = None
        resource.vaccineCode = None
        resource.status = None
        resource.onsetDateTime = None
        resource.effectiveDateTime = None
        resource.authoredOn = None
        resource.performedDateTime = None
        resource.occurrenceDateTime = None
        resource.subject = None
        resource.patient = None
        resource.valueQuantity = None
        resource.clinicalStatus = None

        entry = MagicMock()
        entry.resource = resource
        entries.append(entry)

    bundle = MagicMock()
    bundle.entry = entries
    bundle.total = count
    return bundle


class TestExecuteSearchFhir:
    """execute_search_fhir calls FHIRClient and formats results."""

    @pytest.mark.asyncio
    async def test_empty_search(self) -> None:
        client = _make_mock_fhir_client()
        result = await execute_search_fhir(client, {"resource_type": "Patient"})
        assert "No results found" in result
        client.search.assert_called_once_with("Patient", None)

    @pytest.mark.asyncio
    async def test_search_with_params(self) -> None:
        client = _make_mock_fhir_client()
        params = {"code": "http://snomed.info/sct|44054006"}
        await execute_search_fhir(client, {"resource_type": "Condition", "params": params})
        client.search.assert_called_once_with("Condition", params)

    @pytest.mark.asyncio
    async def test_search_returns_summary(self) -> None:
        bundle = _make_bundle_with_patients(3)
        client = _make_mock_fhir_client(bundle)
        result = await execute_search_fhir(client, {"resource_type": "Patient"})
        assert "Found 3 resources" in result
        assert "Patient" in result


# ---------------------------------------------------------------------------
# format_bundle_summary
# ---------------------------------------------------------------------------


class TestFormatBundleSummary:
    """format_bundle_summary produces token-efficient text."""

    def test_empty_bundle(self) -> None:
        bundle = _make_empty_bundle()
        result = format_bundle_summary(bundle)
        assert "No results found" in result

    def test_patient_summary(self) -> None:
        bundle = _make_bundle_with_patients(2)
        result = format_bundle_summary(bundle)
        assert "Found 2 resources" in result
        assert "Patient" in result
        assert "patient-0" in result
        assert "García" in result

    def test_mixed_bundle(self) -> None:
        """Bundle with Condition and Patient resources."""
        patient = MagicMock()
        patient.get_resource_type.return_value = "Patient"
        patient.id = "p-1"
        name_mock = MagicMock()
        name_mock.family = "López"
        name_mock.given = ["Ana"]
        patient.name = [name_mock]
        patient.gender = "female"
        patient.birthDate = "1970-05-20"
        patient.address = []
        patient.code = None
        patient.medicationCodeableConcept = None
        patient.vaccineCode = None
        patient.status = None
        patient.onsetDateTime = None
        patient.effectiveDateTime = None
        patient.authoredOn = None
        patient.performedDateTime = None
        patient.occurrenceDateTime = None
        patient.subject = None
        patient.patient = None
        patient.valueQuantity = None
        patient.clinicalStatus = None

        condition = MagicMock()
        condition.get_resource_type.return_value = "Condition"
        condition.id = "c-1"
        condition.name = None
        condition.gender = None
        condition.birthDate = None
        condition.address = None
        condition.medicationCodeableConcept = None
        condition.vaccineCode = None
        condition.status = None
        condition.effectiveDateTime = None
        condition.authoredOn = None
        condition.performedDateTime = None
        condition.occurrenceDateTime = None
        condition.patient = None
        condition.valueQuantity = None

        # Code with coding
        coding = MagicMock()
        coding.display = "Diabetes mellitus tipo 2"
        coding.code = "44054006"
        coding.system = "http://snomed.info/sct"
        codeable = MagicMock()
        codeable.text = None
        codeable.coding = [coding]
        condition.code = codeable

        # Subject reference
        subject_ref = MagicMock()
        subject_ref.reference = "Patient/p-1"
        condition.subject = subject_ref

        condition.onsetDateTime = "2020-01-15"
        clinical_status = MagicMock()
        clinical_status.text = "active"
        clinical_status.coding = None
        condition.clinicalStatus = clinical_status

        entry_p = MagicMock()
        entry_p.resource = patient
        entry_c = MagicMock()
        entry_c.resource = condition

        bundle = MagicMock()
        bundle.entry = [entry_c, entry_p]
        bundle.total = 2

        result = format_bundle_summary(bundle)
        assert "Found 2 resources" in result
        assert "1 Condition" in result
        assert "1 Patient" in result
        assert "Diabetes mellitus tipo 2" in result
        assert "Patient/p-1" in result

    def test_null_resource_entry_skipped(self) -> None:
        entry = MagicMock()
        entry.resource = None
        bundle = MagicMock()
        bundle.entry = [entry]
        bundle.total = 0

        result = format_bundle_summary(bundle)
        assert "Found 0 resources" in result


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    """ToolRegistry manages tool definitions and execution."""

    def test_definitions_with_resolver(self) -> None:
        client = MagicMock()
        resolver = MagicMock()
        registry = ToolRegistry(fhir_client=client, terminology_resolver=resolver)
        defs = registry.definitions()
        names = {d["name"] for d in defs}
        assert names == {"resolve_terminology", "search_fhir"}

    def test_definitions_without_resolver(self) -> None:
        client = MagicMock()
        registry = ToolRegistry(fhir_client=client, terminology_resolver=None)
        defs = registry.definitions()
        names = {d["name"] for d in defs}
        assert names == {"search_fhir"}

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self) -> None:
        client = MagicMock()
        registry = ToolRegistry(fhir_client=client)
        tc = ToolCall(id="tc_1", name="unknown_tool", arguments={})
        result = await registry.execute(tc)
        assert result.is_error is True
        assert "unknown tool" in result.content

    @pytest.mark.asyncio
    async def test_execute_resolve_terminology(self) -> None:
        client = MagicMock()
        resolver = _make_mock_resolver()
        registry = ToolRegistry(fhir_client=client, terminology_resolver=resolver)
        tc = ToolCall(
            id="tc_1",
            name="resolve_terminology",
            arguments={"term": "diabetes"},
        )
        result = await registry.execute(tc)
        assert result.is_error is False
        data = json.loads(result.content)
        assert data["code"] == "44054006"

    @pytest.mark.asyncio
    async def test_execute_search_fhir(self) -> None:
        bundle = _make_empty_bundle()
        client = MagicMock()
        client.search = AsyncMock(return_value=bundle)
        registry = ToolRegistry(fhir_client=client)
        tc = ToolCall(
            id="tc_1",
            name="search_fhir",
            arguments={"resource_type": "Patient"},
        )
        result = await registry.execute(tc)
        assert result.is_error is False
        assert "No results found" in result.content

    @pytest.mark.asyncio
    async def test_execute_tool_error_raises(self) -> None:
        client = MagicMock()
        client.search = AsyncMock(side_effect=Exception("connection failed"))
        registry = ToolRegistry(fhir_client=client)
        tc = ToolCall(
            id="tc_1",
            name="search_fhir",
            arguments={"resource_type": "Patient"},
        )
        with pytest.raises(ToolExecutionError, match="connection failed"):
            await registry.execute(tc)
