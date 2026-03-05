"""Tests for saludai_agent.tools — tool definitions, executors, and registry."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from saludai_agent.exceptions import ToolExecutionError
from saludai_agent.tools import (
    EXECUTE_CODE_DEFINITION,
    GET_RESOURCE_DEFINITION,
    RESOLVE_TERMINOLOGY_DEFINITION,
    SEARCH_FHIR_DEFINITION,
    ToolRegistry,
    _extract_extensions,
    execute_code,
    execute_get_resource,
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

    def test_get_resource_name(self) -> None:
        assert GET_RESOURCE_DEFINITION["name"] == "get_resource"

    def test_get_resource_has_description(self) -> None:
        assert len(GET_RESOURCE_DEFINITION["description"]) > 10

    def test_get_resource_required_fields(self) -> None:
        schema = GET_RESOURCE_DEFINITION["input_schema"]
        assert "resource_type" in schema["properties"]
        assert "resource_id" in schema["properties"]
        assert set(schema["required"]) == {"resource_type", "resource_id"}

    def test_execute_code_name(self) -> None:
        assert EXECUTE_CODE_DEFINITION["name"] == "execute_code"

    def test_execute_code_has_description(self) -> None:
        assert len(EXECUTE_CODE_DEFINITION["description"]) > 10

    def test_execute_code_required_fields(self) -> None:
        schema = EXECUTE_CODE_DEFINITION["input_schema"]
        assert "code" in schema["properties"]
        assert "code" in schema["required"]


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
    """Create a mock FHIRClient that returns dicts (like the real client)."""
    client = MagicMock()
    client.search = AsyncMock(return_value=bundle or _make_empty_bundle())
    return client


def _make_empty_bundle() -> dict[str, Any]:
    """Create an empty FHIR Bundle dict."""
    return {"resourceType": "Bundle", "type": "searchset", "total": 0}


def _make_bundle_with_patients(count: int = 2) -> dict[str, Any]:
    """Create a FHIR Bundle dict with Patient resources."""
    entries = []
    for i in range(count):
        entries.append(
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": f"patient-{i}",
                    "name": [{"family": "García", "given": ["Juan"]}],
                    "gender": "male",
                    "birthDate": "1960-01-15",
                    "address": [],
                }
            }
        )
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": count,
        "entry": entries,
    }


class TestExecuteSearchFhir:
    """execute_search_fhir calls FHIRClient and formats results."""

    @pytest.mark.asyncio
    async def test_empty_search(self) -> None:
        client = _make_mock_fhir_client()
        result = await execute_search_fhir(client, {"resource_type": "Patient"})
        assert "No results found" in result
        # Default _count=200 is injected
        client.search.assert_called_once_with("Patient", {"_count": "200"})

    @pytest.mark.asyncio
    async def test_search_with_params(self) -> None:
        client = _make_mock_fhir_client()
        params = {"code": "http://snomed.info/sct|44054006"}
        await execute_search_fhir(client, {"resource_type": "Condition", "params": params})
        # _count=200 injected alongside existing params
        client.search.assert_called_once_with(
            "Condition", {"code": "http://snomed.info/sct|44054006", "_count": "200"}
        )

    @pytest.mark.asyncio
    async def test_search_returns_summary(self) -> None:
        bundle = _make_bundle_with_patients(3)
        client = _make_mock_fhir_client(bundle)
        result = await execute_search_fhir(client, {"resource_type": "Patient"})
        assert "Found 3 resources" in result
        assert "Patient" in result

    @pytest.mark.asyncio
    async def test_default_count_not_injected_when_count_present(self) -> None:
        client = _make_mock_fhir_client()
        params = {"_count": "50"}
        await execute_search_fhir(client, {"resource_type": "Patient", "params": params})
        client.search.assert_called_once_with("Patient", {"_count": "50"})

    @pytest.mark.asyncio
    async def test_default_count_not_injected_when_summary_present(self) -> None:
        client = _make_mock_fhir_client()
        params = {"_summary": "count"}
        await execute_search_fhir(client, {"resource_type": "Patient", "params": params})
        client.search.assert_called_once_with("Patient", {"_summary": "count"})


# ---------------------------------------------------------------------------
# execute_get_resource
# ---------------------------------------------------------------------------


class TestExecuteGetResource:
    """execute_get_resource reads a single resource via FHIRClient.read_raw."""

    @pytest.mark.asyncio
    async def test_returns_summary(self) -> None:
        client = MagicMock()
        client.read_raw = AsyncMock(
            return_value={
                "resourceType": "Patient",
                "id": "1005",
                "name": [{"family": "García", "given": ["Ana"]}],
                "gender": "female",
                "birthDate": "1980-03-15",
                "address": [{"city": "Buenos Aires", "state": "CABA"}],
            }
        )
        result = await execute_get_resource(
            client,
            {
                "resource_type": "Patient",
                "resource_id": "1005",
            },
        )
        assert "Patient/1005" in result
        assert "García" in result
        assert "1980-03-15" in result

    @pytest.mark.asyncio
    async def test_propagates_not_found(self) -> None:
        from saludai_core.exceptions import FHIRResourceNotFoundError

        client = MagicMock()
        client.read_raw = AsyncMock(
            side_effect=FHIRResourceNotFoundError("Resource not found: GET /Patient/9999")
        )
        with pytest.raises(FHIRResourceNotFoundError):
            await execute_get_resource(
                client,
                {
                    "resource_type": "Patient",
                    "resource_id": "9999",
                },
            )


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
        bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 2,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "c-1",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "44054006",
                                    "display": "Diabetes mellitus tipo 2",
                                }
                            ],
                        },
                        "subject": {"reference": "Patient/p-1"},
                        "onsetDateTime": "2020-01-15",
                        "clinicalStatus": {"text": "active"},
                    }
                },
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "p-1",
                        "name": [{"family": "López", "given": ["Ana"]}],
                        "gender": "female",
                        "birthDate": "1970-05-20",
                        "address": [],
                    }
                },
            ],
        }

        result = format_bundle_summary(bundle)
        assert "Found 2 resources" in result
        assert "1 Condition" in result
        assert "1 Patient" in result
        assert "Diabetes mellitus tipo 2" in result
        assert "Patient/p-1" in result

    def test_summary_count_bundle(self) -> None:
        """_summary=count returns total but no entries."""
        bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 55,
        }
        result = format_bundle_summary(bundle)
        assert "Total count: 55" in result
        assert "summary-only" in result
        assert "No results found" not in result

    def test_summary_count_zero(self) -> None:
        """_summary=count with total=0 should say no results."""
        bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
        }
        result = format_bundle_summary(bundle)
        assert "No results found" in result

    def test_empty_bundle_no_total(self) -> None:
        """Bundle with no entries and no total."""
        bundle: dict[str, Any] = {"resourceType": "Bundle", "type": "searchset"}
        result = format_bundle_summary(bundle)
        assert "No results found" in result

    def test_null_resource_entry_skipped(self) -> None:
        bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
            "entry": [{"resource": None}],
        }

        result = format_bundle_summary(bundle)
        assert "Found 0 resources" in result


# ---------------------------------------------------------------------------
# execute_code
# ---------------------------------------------------------------------------


class TestExecuteCode:
    """execute_code runs sandboxed Python and captures output."""

    def test_simple_print(self) -> None:
        result = execute_code({"code": "print('hello')"})
        assert result.strip() == "hello"

    def test_counter_aggregation(self) -> None:
        code = (
            "from collections import Counter\n"
            "data = ['a', 'b', 'a', 'c', 'a', 'b']\n"
            "print(Counter(data).most_common())"
        )
        result = execute_code({"code": code})
        assert "('a', 3)" in result

    def test_datetime_available(self) -> None:
        result = execute_code({"code": "print(datetime.date(2024, 1, 1).isoformat())"})
        assert "2024-01-01" in result

    def test_json_available(self) -> None:
        result = execute_code({"code": "print(json.dumps({'key': 'value'}))"})
        assert '"key"' in result

    def test_math_available(self) -> None:
        result = execute_code({"code": "print(math.sqrt(144))"})
        assert "12" in result

    def test_statistics_available(self) -> None:
        result = execute_code({"code": "print(statistics.mean([10, 20, 30]))"})
        assert "20" in result

    def test_re_available(self) -> None:
        result = execute_code({"code": "print(re.findall(r'\\d+', 'abc123def456'))"})
        assert "123" in result

    def test_multiple_prints(self) -> None:
        code = "print('line1')\nprint('line2')"
        result = execute_code({"code": code})
        assert "line1" in result
        assert "line2" in result

    # -- Security tests --

    def test_no_file_access(self) -> None:
        result = execute_code({"code": "open('test.txt', 'w')"})
        assert "Error" in result

    def test_no_import_os(self) -> None:
        result = execute_code({"code": "import os"})
        assert "Error" in result

    def test_no_import_subprocess(self) -> None:
        result = execute_code({"code": "import subprocess"})
        assert "Error" in result

    def test_no_eval(self) -> None:
        result = execute_code({"code": "eval('1+1')"})
        assert "Error" in result

    def test_no_exec(self) -> None:
        result = execute_code({"code": "exec('print(1)')"})
        assert "Error" in result

    def test_no_dunder_import(self) -> None:
        result = execute_code({"code": "__import__('os')"})
        assert "Error" in result

    # -- Edge cases --

    def test_timeout_infinite_loop(self) -> None:
        result = execute_code({"code": "while True: pass"})
        assert "timed out" in result

    def test_empty_code(self) -> None:
        result = execute_code({"code": ""})
        assert "Error" in result

    def test_no_output_hint(self) -> None:
        result = execute_code({"code": "x = 42"})
        assert "No output" in result
        assert "print" in result

    def test_output_truncation(self) -> None:
        code = "print('x' * 5000)"
        result = execute_code({"code": code})
        assert len(result) <= 4100  # 4000 + truncation message
        assert "truncated" in result

    def test_syntax_error(self) -> None:
        result = execute_code({"code": "def foo(:"})
        assert "Error" in result
        assert "SyntaxError" in result

    def test_runtime_error(self) -> None:
        result = execute_code({"code": "print(1/0)"})
        assert "Error" in result
        assert "ZeroDivisionError" in result


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
        assert names == {"resolve_terminology", "search_fhir", "get_resource", "execute_code"}

    def test_definitions_without_resolver(self) -> None:
        client = MagicMock()
        registry = ToolRegistry(fhir_client=client, terminology_resolver=None)
        defs = registry.definitions()
        names = {d["name"] for d in defs}
        assert names == {"search_fhir", "get_resource", "execute_code"}

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
    async def test_execute_get_resource(self) -> None:
        client = MagicMock()
        client.read_raw = AsyncMock(
            return_value={
                "resourceType": "Patient",
                "id": "p-1",
                "name": [{"family": "Test", "given": ["User"]}],
                "gender": "male",
                "birthDate": "1990-01-01",
                "address": [],
            }
        )
        registry = ToolRegistry(fhir_client=client)
        tc = ToolCall(
            id="tc_1",
            name="get_resource",
            arguments={"resource_type": "Patient", "resource_id": "p-1"},
        )
        result = await registry.execute(tc)
        assert result.is_error is False
        assert "Patient/p-1" in result.content

    @pytest.mark.asyncio
    async def test_execute_code_via_registry(self) -> None:
        client = MagicMock()
        registry = ToolRegistry(fhir_client=client)
        tc = ToolCall(
            id="tc_1",
            name="execute_code",
            arguments={"code": "print(2 + 3)"},
        )
        result = await registry.execute(tc)
        assert result.is_error is False
        assert "5" in result.content

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


# ---------------------------------------------------------------------------
# Extension extraction
# ---------------------------------------------------------------------------


def _make_ext_def(
    url: str = "http://example.com/ext",
    name: str = "TestExt",
    value_type: str = "string",
    context: str = "Patient",
) -> Any:
    """Create an ExtensionDef-like object for tests."""
    from saludai_core.locales._types import ExtensionDef

    return ExtensionDef(
        url=url,
        name=name,
        description="test",
        value_type=value_type,
        context=context,
    )


class TestExtractExtensions:
    """_extract_extensions translates extension URLs into name=value pairs."""

    def test_string_extension(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/fathers-family",
            name="Apellido paterno",
            value_type="string",
        )
        resource: dict[str, Any] = {
            "extension": [
                {"url": "http://example.com/fathers-family", "valueString": "González"},
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == ["Apellido paterno=González"]

    def test_boolean_extension(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/matricula",
            name="Matricula habilitada",
            value_type="boolean",
        )
        resource: dict[str, Any] = {
            "extension": [
                {"url": "http://example.com/matricula", "valueBoolean": True},
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == ["Matricula habilitada=True"]

    def test_code_extension(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/status",
            name="Estado",
            value_type="code",
        )
        resource: dict[str, Any] = {
            "extension": [
                {"url": "http://example.com/status", "valueCode": "active"},
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == ["Estado=active"]

    def test_codeable_concept_extension(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/etnia",
            name="Etnia",
            value_type="CodeableConcept",
        )
        resource: dict[str, Any] = {
            "extension": [
                {
                    "url": "http://example.com/etnia",
                    "valueCodeableConcept": {
                        "coding": [{"code": "12345", "display": "Mapuche"}],
                    },
                },
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert len(result) == 1
        assert "Etnia=" in result[0]
        assert "Mapuche" in result[0]

    def test_coding_extension(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/esquema",
            name="Esquema NOMIVAC",
            value_type="Coding",
        )
        resource: dict[str, Any] = {
            "extension": [
                {
                    "url": "http://example.com/esquema",
                    "valueCoding": {"code": "BCG", "display": "BCG neonatal"},
                },
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == ["Esquema NOMIVAC=BCG neonatal"]

    def test_coding_extension_fallback_to_code(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/esquema",
            name="Esquema",
            value_type="Coding",
        )
        resource: dict[str, Any] = {
            "extension": [
                {"url": "http://example.com/esquema", "valueCoding": {"code": "BCG"}},
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == ["Esquema=BCG"]

    def test_address_extension(self) -> None:
        ext_def = _make_ext_def(
            url="http://example.com/birthPlace",
            name="Lugar de nacimiento",
            value_type="Address",
        )
        resource: dict[str, Any] = {
            "extension": [
                {
                    "url": "http://example.com/birthPlace",
                    "valueAddress": {
                        "city": "Rosario",
                        "state": "Santa Fe",
                        "country": "Argentina",
                    },
                },
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == ["Lugar de nacimiento=Rosario, Santa Fe, Argentina"]

    def test_unknown_url_skipped(self) -> None:
        ext_def = _make_ext_def(url="http://example.com/known")
        resource: dict[str, Any] = {
            "extension": [
                {"url": "http://example.com/unknown", "valueString": "ignored"},
            ],
        }
        result = _extract_extensions(resource, [ext_def])
        assert result == []

    def test_no_extensions_on_resource(self) -> None:
        ext_def = _make_ext_def()
        resource: dict[str, Any] = {"id": "1"}
        result = _extract_extensions(resource, [ext_def])
        assert result == []

    def test_empty_extension_defs(self) -> None:
        resource: dict[str, Any] = {
            "extension": [{"url": "http://example.com/ext", "valueString": "x"}],
        }
        result = _extract_extensions(resource, [])
        assert result == []

    def test_integration_with_summarize_resource(self) -> None:
        """Extensions appear in _summarize_resource output."""
        from saludai_agent.tools import _summarize_resource

        ext_def = _make_ext_def(
            url="http://example.com/etnia",
            name="Etnia",
            value_type="string",
        )
        resource: dict[str, Any] = {
            "resourceType": "Patient",
            "id": "p-1",
            "name": [{"family": "García", "given": ["Juan"]}],
            "gender": "male",
            "birthDate": "1990-01-01",
            "address": [],
            "extension": [
                {"url": "http://example.com/etnia", "valueString": "Mapuche"},
            ],
        }
        result = _summarize_resource("Patient", resource, extension_defs=[ext_def])
        assert "Etnia=Mapuche" in result
        assert "Patient/p-1" in result

    def test_integration_with_format_bundle_summary(self) -> None:
        """Extensions appear in format_bundle_summary output."""
        ext_def = _make_ext_def(
            url="http://example.com/etnia",
            name="Etnia",
            value_type="string",
        )
        bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "p-1",
                        "name": [{"family": "López", "given": ["Ana"]}],
                        "gender": "female",
                        "birthDate": "1985-03-10",
                        "address": [],
                        "extension": [
                            {"url": "http://example.com/etnia", "valueString": "Guaraní"},
                        ],
                    }
                }
            ],
        }
        result = format_bundle_summary(bundle, extension_defs=[ext_def])
        assert "Etnia=Guaraní" in result

    @pytest.mark.asyncio
    async def test_registry_passes_extension_defs(self) -> None:
        """ToolRegistry passes locale pack extensions to summarizer."""
        from saludai_core.locales._types import ExtensionDef, LocalePack

        ext = ExtensionDef(
            url="http://example.com/etnia",
            name="Etnia",
            description="test",
            value_type="string",
            context="Patient",
        )
        locale_pack = LocalePack(
            code="test",
            name="Test",
            language="en",
            terminology_systems=(),
            system_prompt="test",
            tool_descriptions={},
            tool_system_enum=(),
            extensions=(ext,),
        )
        client = MagicMock()
        client.read_raw = AsyncMock(
            return_value={
                "resourceType": "Patient",
                "id": "p-1",
                "name": [{"family": "Test", "given": ["User"]}],
                "gender": "male",
                "birthDate": "1990-01-01",
                "address": [],
                "extension": [
                    {"url": "http://example.com/etnia", "valueString": "Quechua"},
                ],
            }
        )
        registry = ToolRegistry(fhir_client=client, locale_pack=locale_pack)
        tc = ToolCall(
            id="tc_1",
            name="get_resource",
            arguments={"resource_type": "Patient", "resource_id": "p-1"},
        )
        result = await registry.execute(tc)
        assert "Etnia=Quechua" in result.content
