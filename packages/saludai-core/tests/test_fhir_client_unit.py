"""Unit tests for FHIRClient (no running server required).

Tests all code paths using mocked HTTP responses — no HAPI FHIR needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from saludai_core.config import FHIRConfig
from saludai_core.exceptions import (
    FHIRAuthenticationError,
    FHIRConnectionError,
    FHIRResourceNotFoundError,
    FHIRValidationError,
)
from saludai_core.fhir_client import FHIRClient, _get_resource_class
from saludai_core.query_builder import FHIRQueryBuilder


def _make_bundle(
    entries: list[dict[str, Any]],
    total: int | None = None,
    next_url: str | None = None,
) -> dict[str, Any]:
    """Build a minimal FHIR Bundle dict."""
    bundle: dict[str, Any] = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": entries,
    }
    if total is not None:
        bundle["total"] = total
    if next_url is not None:
        bundle["link"] = [{"relation": "next", "url": next_url}]
    return bundle


def _make_patient_entry(pid: str) -> dict[str, Any]:
    return {
        "resource": {
            "resourceType": "Patient",
            "id": pid,
        }
    }


class TestGetNextLink:
    """FHIRClient._get_next_link extracts next URL from bundle."""

    def test_extracts_next_url(self) -> None:
        bundle = _make_bundle([], next_url="http://fhir/Patient?_count=10&_getpagesoffset=10")
        assert (
            FHIRClient._get_next_link(bundle) == "http://fhir/Patient?_count=10&_getpagesoffset=10"
        )

    def test_returns_none_when_no_links(self) -> None:
        bundle = _make_bundle([])
        assert FHIRClient._get_next_link(bundle) is None

    def test_returns_none_when_no_next_relation(self) -> None:
        bundle = {
            "resourceType": "Bundle",
            "link": [{"relation": "self", "url": "http://fhir/Patient"}],
        }
        assert FHIRClient._get_next_link(bundle) is None


class TestSearchAll:
    """FHIRClient.search_all follows pagination next links."""

    @pytest.mark.asyncio
    async def test_single_page_no_next(self) -> None:
        """Returns single page when there's no next link."""
        entries = [_make_patient_entry("1"), _make_patient_entry("2")]
        bundle = _make_bundle(entries, total=2)

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=bundle)  # type: ignore[method-assign]

        result = await client.search_all("Patient")
        assert len(result["entry"]) == 2
        assert result["total"] == 2
        client.search.assert_called_once_with("Patient", None)

    @pytest.mark.asyncio
    async def test_follows_next_links(self) -> None:
        """Merges entries from multiple pages."""
        page1 = _make_bundle(
            [_make_patient_entry("1"), _make_patient_entry("2")],
            total=4,
            next_url="http://fake:8080/fhir/Patient?_getpagesoffset=2",
        )
        page2 = _make_bundle(
            [_make_patient_entry("3"), _make_patient_entry("4")],
            total=4,
        )

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=page1)  # type: ignore[method-assign]
        client._request_url = AsyncMock(return_value=page2)  # type: ignore[method-assign]

        result = await client.search_all("Patient")
        assert len(result["entry"]) == 4
        assert result["total"] == 4
        client._request_url.assert_called_once_with(
            "http://fake:8080/fhir/Patient?_getpagesoffset=2"
        )

    @pytest.mark.asyncio
    async def test_respects_max_pages(self) -> None:
        """Stops after max_pages even if more pages available."""
        page = _make_bundle(
            [_make_patient_entry("1")],
            total=100,
            next_url="http://fake:8080/fhir/Patient?_getpagesoffset=1",
        )

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=page)  # type: ignore[method-assign]
        client._request_url = AsyncMock(return_value=page)  # type: ignore[method-assign]

        result = await client.search_all("Patient", max_pages=3)
        # 1 initial + 2 next pages = 3 entries
        assert len(result["entry"]) == 3
        assert client._request_url.call_count == 2

    @pytest.mark.asyncio
    async def test_stops_on_empty_page(self) -> None:
        """Stops when a page returns no entries."""
        page1 = _make_bundle(
            [_make_patient_entry("1")],
            total=2,
            next_url="http://fake:8080/fhir/Patient?_getpagesoffset=1",
        )
        page2 = _make_bundle([], total=2)

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=page1)  # type: ignore[method-assign]
        client._request_url = AsyncMock(return_value=page2)  # type: ignore[method-assign]

        result = await client.search_all("Patient")
        assert len(result["entry"]) == 1

    @pytest.mark.asyncio
    async def test_preserves_server_total(self) -> None:
        """The merged bundle uses the server total from the first page."""
        page1 = _make_bundle(
            [_make_patient_entry("1")],
            total=300,
            next_url="http://fake:8080/fhir/next",
        )
        page2 = _make_bundle([_make_patient_entry("2")], total=300)

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=page1)  # type: ignore[method-assign]
        client._request_url = AsyncMock(return_value=page2)  # type: ignore[method-assign]

        result = await client.search_all("Patient")
        assert result["total"] == 300

    @pytest.mark.asyncio
    async def test_no_total_in_bundle(self) -> None:
        """Works when server doesn't return total."""
        page = _make_bundle([_make_patient_entry("1")])

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=page)  # type: ignore[method-assign]

        result = await client.search_all("Patient")
        assert len(result["entry"]) == 1
        assert "total" not in result

    @pytest.mark.asyncio
    async def test_passes_params_to_search(self) -> None:
        """Forwards params to the initial search call."""
        page = _make_bundle([_make_patient_entry("1")], total=1)

        config = FHIRConfig(fhir_server_url="http://fake:8080/fhir")
        client = FHIRClient(config)
        client.search = AsyncMock(return_value=page)  # type: ignore[method-assign]

        params = {"code": "http://snomed.info/sct|44054006", "_count": "200"}
        await client.search_all("Condition", params)
        client.search.assert_called_once_with("Condition", params)


# ---------------------------------------------------------------------------
# Helpers for httpx.MockTransport-based tests
# ---------------------------------------------------------------------------

CAPABILITY_STATEMENT: dict[str, Any] = {
    "resourceType": "CapabilityStatement",
    "status": "active",
    "kind": "instance",
    "fhirVersion": "4.0.1",
    "format": ["json"],
    "date": "2024-01-01",
}

PATIENT_JSON: dict[str, Any] = {
    "resourceType": "Patient",
    "id": "p-123",
    "name": [{"family": "García", "given": ["María"]}],
    "gender": "female",
    "birthDate": "1990-01-15",
}

BUNDLE_JSON: dict[str, Any] = {
    "resourceType": "Bundle",
    "type": "searchset",
    "total": 1,
    "entry": [{"resource": PATIENT_JSON}],
}


def _mock_client(
    handler: Any,
    *,
    auth_type: str = "none",
    auth_token: str | None = None,
) -> FHIRClient:
    """Create a FHIRClient with a mocked httpx transport."""
    config = FHIRConfig(
        fhir_server_url="http://fhir-test:8080/fhir",
        fhir_auth_type=auth_type,  # type: ignore[arg-type]
        fhir_auth_token=auth_token,
        fhir_timeout=5.0,
    )
    client = FHIRClient(config)
    # Replace internal httpx client with mocked transport
    client._http = httpx.AsyncClient(
        base_url=config.fhir_server_url,
        headers=dict(client._http.headers),
        timeout=config.fhir_timeout,
        transport=httpx.MockTransport(handler),
    )
    return client


# ---------------------------------------------------------------------------
# _get_resource_class
# ---------------------------------------------------------------------------


class TestGetResourceClass:
    def test_valid_patient(self) -> None:
        cls = _get_resource_class("Patient")
        assert cls.__name__ == "Patient"

    def test_valid_condition(self) -> None:
        cls = _get_resource_class("Condition")
        assert cls.__name__ == "Condition"

    def test_unknown_raises(self) -> None:
        with pytest.raises(FHIRValidationError, match="Unknown FHIR resource type"):
            _get_resource_class("FakeResource")


# ---------------------------------------------------------------------------
# FHIRClient.__init__ — auth header
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_no_auth_header(self) -> None:
        config = FHIRConfig(fhir_auth_type="none")
        client = FHIRClient(config)
        assert "Authorization" not in client._http.headers

    def test_bearer_auth_header(self) -> None:
        config = FHIRConfig(fhir_auth_type="bearer", fhir_auth_token="tok-123")
        client = FHIRClient(config)
        assert client._http.headers["Authorization"] == "Bearer tok-123"

    def test_bearer_no_token_no_header(self) -> None:
        config = FHIRConfig(fhir_auth_type="bearer", fhir_auth_token=None)
        client = FHIRClient(config)
        assert "Authorization" not in client._http.headers


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------


class TestCheckConnection:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=CAPABILITY_STATEMENT)

        async with _mock_client(handler) as client:
            cap = await client.check_connection()
            assert cap.get_resource_type() == "CapabilityStatement"

    @pytest.mark.asyncio
    async def test_non_r4_raises(self) -> None:
        bad_cap = {**CAPABILITY_STATEMENT, "fhirVersion": "3.0.2"}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=bad_cap)

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError, match="Expected FHIR R4"):
                await client.check_connection()

    @pytest.mark.asyncio
    async def test_invalid_response_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=b"not json",
                headers={"content-type": "text/plain"},
            )

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError):
                await client.check_connection()


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


class TestRead:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/Patient/p-123" in str(request.url)
            return httpx.Response(200, json=PATIENT_JSON)

        async with _mock_client(handler) as client:
            patient = await client.read("Patient", "p-123")
            assert patient.get_resource_type() == "Patient"
            assert patient.id == "p-123"

    @pytest.mark.asyncio
    async def test_404_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"issue": "not found"})

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRResourceNotFoundError):
                await client.read("Patient", "nonexistent")

    @pytest.mark.asyncio
    async def test_parse_error_raises(self) -> None:
        # CapabilityStatement requires 'status', 'kind', 'fhirVersion', 'format', 'date'
        # Passing garbage triggers Pydantic validation
        bad = {"resourceType": "CapabilityStatement"}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=bad)

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError, match="Failed to parse"):
                await client.read("CapabilityStatement", "x")


# ---------------------------------------------------------------------------
# read_raw
# ---------------------------------------------------------------------------


class TestReadRaw:
    @pytest.mark.asyncio
    async def test_returns_dict(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=PATIENT_JSON)

        async with _mock_client(handler) as client:
            data = await client.read_raw("Patient", "p-123")
            assert data["resourceType"] == "Patient"
            assert data["id"] == "p-123"

    @pytest.mark.asyncio
    async def test_404_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={})

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRResourceNotFoundError):
                await client.read_raw("Patient", "nope")


# ---------------------------------------------------------------------------
# search (with transport mock)
# ---------------------------------------------------------------------------


class TestSearchTransport:
    @pytest.mark.asyncio
    async def test_with_params(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "name=Garcia" in str(request.url)
            return httpx.Response(200, json=BUNDLE_JSON)

        async with _mock_client(handler) as client:
            bundle = await client.search("Patient", {"name": "Garcia"})
            assert bundle["resourceType"] == "Bundle"

    @pytest.mark.asyncio
    async def test_with_list_params(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            assert "_include=" in url
            return httpx.Response(200, json=BUNDLE_JSON)

        async with _mock_client(handler) as client:
            bundle = await client.search(
                "Condition",
                {"_include": ["Condition:subject", "Condition:encounter"]},
            )
            assert bundle["resourceType"] == "Bundle"

    @pytest.mark.asyncio
    async def test_none_params(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=BUNDLE_JSON)

        async with _mock_client(handler) as client:
            bundle = await client.search("Patient", None)
            assert bundle["resourceType"] == "Bundle"


# ---------------------------------------------------------------------------
# execute (FHIRQuery)
# ---------------------------------------------------------------------------


class TestExecute:
    @pytest.mark.asyncio
    async def test_delegates_to_search(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            assert "/Patient" in url
            assert "_count=5" in url
            return httpx.Response(200, json=BUNDLE_JSON)

        async with _mock_client(handler) as client:
            query = FHIRQueryBuilder("Patient").count(5).build()
            bundle = await client.execute(query)
            assert bundle["resourceType"] == "Bundle"


# ---------------------------------------------------------------------------
# close / context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    @pytest.mark.asyncio
    async def test_async_with(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=BUNDLE_JSON)

        client = _mock_client(handler)
        async with client as c:
            assert c is client

    @pytest.mark.asyncio
    async def test_close_explicit(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=BUNDLE_JSON)

        client = _mock_client(handler)
        await client.close()


# ---------------------------------------------------------------------------
# _request — HTTP error mapping
# ---------------------------------------------------------------------------


class TestRequestErrors:
    @pytest.mark.asyncio
    async def test_401_raises_auth(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "unauthorized"})

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRAuthenticationError, match="401"):
                await client.search("Patient")

    @pytest.mark.asyncio
    async def test_403_raises_auth(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"error": "forbidden"})

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRAuthenticationError, match="403"):
                await client.search("Patient")

    @pytest.mark.asyncio
    async def test_500_raises_validation(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError, match="500"):
                await client.search("Patient")

    @pytest.mark.asyncio
    async def test_non_json_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=b"<html>oops</html>",
                headers={"content-type": "text/html"},
            )

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError, match="non-JSON"):
                await client.search("Patient")

    @pytest.mark.asyncio
    async def test_connect_error_raises(self) -> None:
        config = FHIRConfig(
            fhir_server_url="http://localhost:19999/fhir",
            fhir_timeout=1.0,
        )
        async with FHIRClient(config) as client:
            with pytest.raises(FHIRConnectionError):
                await client.search("Patient")


# ---------------------------------------------------------------------------
# _request_url — errors during pagination
# ---------------------------------------------------------------------------


class TestRequestUrlErrors:
    @pytest.mark.asyncio
    async def test_400_on_next_page(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                page1 = _make_bundle(
                    [_make_patient_entry("1")],
                    next_url="http://fhir-test:8080/fhir/Patient?_offset=1",
                )
                return httpx.Response(200, json=page1)
            return httpx.Response(400, text="Bad Request")

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError, match="400"):
                await client.search_all("Patient")

    @pytest.mark.asyncio
    async def test_non_json_next_page(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                page1 = _make_bundle(
                    [_make_patient_entry("1")],
                    next_url="http://fhir-test:8080/fhir/Patient?_offset=1",
                )
                return httpx.Response(200, json=page1)
            return httpx.Response(
                200,
                content=b"not json",
                headers={"content-type": "text/plain"},
            )

        async with _mock_client(handler) as client:
            with pytest.raises(FHIRValidationError, match="non-JSON"):
                await client.search_all("Patient")


# ---------------------------------------------------------------------------
# _build_query_params
# ---------------------------------------------------------------------------


class TestBuildQueryParams:
    def test_none_returns_none(self) -> None:
        assert FHIRClient._build_query_params(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert FHIRClient._build_query_params({}) is None

    def test_simple_params(self) -> None:
        result = FHIRClient._build_query_params({"name": "Garcia", "_count": "10"})
        assert result is not None
        assert ("name", "Garcia") in result
        assert ("_count", "10") in result

    def test_list_params_expanded(self) -> None:
        result = FHIRClient._build_query_params(
            {"_include": ["Condition:subject", "Condition:encounter"]}
        )
        assert result is not None
        assert ("_include", "Condition:subject") in result
        assert ("_include", "Condition:encounter") in result
        assert len(result) == 2
