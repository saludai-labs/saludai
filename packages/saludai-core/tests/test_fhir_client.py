"""Integration tests for FHIRClient against a running HAPI FHIR server.

These tests require ``docker compose up`` to be running with seeded data
(55 patients, 80 conditions).  They are marked with ``@pytest.mark.integration``
so they can be run selectively::

    uv run pytest -m integration -v
"""

from __future__ import annotations

import httpx
import pytest

from saludai_core.config import FHIRConfig
from saludai_core.exceptions import FHIRConnectionError, FHIRResourceNotFoundError
from saludai_core.fhir_client import FHIRClient

FHIR_BASE = "http://localhost:8080/fhir"


def _hapi_is_running() -> bool:
    """Return True if HAPI FHIR is reachable."""
    try:
        r = httpx.get(f"{FHIR_BASE}/metadata", timeout=5)
        return r.status_code == 200
    except httpx.ConnectError:
        return False


skip_no_hapi = pytest.mark.skipif(
    not _hapi_is_running(),
    reason="HAPI FHIR server is not running (docker compose up)",
)

pytestmark = [pytest.mark.integration, skip_no_hapi]


@pytest.fixture
async def client() -> FHIRClient:
    """Create a FHIRClient connected to the local HAPI instance."""
    config = FHIRConfig(fhir_server_url=FHIR_BASE)
    async with FHIRClient(config) as c:
        yield c  # type: ignore[misc]


async def test_check_connection(client: FHIRClient) -> None:
    """check_connection returns a CapabilityStatement for FHIR R4."""
    cap = await client.check_connection()
    assert cap.get_resource_type() == "CapabilityStatement"
    assert str(cap.fhirVersion).startswith("4.")


async def test_search_patients(client: FHIRClient) -> None:
    """Searching patients returns a Bundle dict with at least 50 entries."""
    bundle = await client.search("Patient", {"_count": "100"})
    assert bundle["resourceType"] == "Bundle"
    assert bundle["total"] >= 50


async def test_search_patients_by_address_state(client: FHIRClient) -> None:
    """Searching patients by address-state filters correctly."""
    bundle = await client.search("Patient", {"address-state": "Buenos Aires"})
    assert bundle["resourceType"] == "Bundle"
    assert bundle.get("entry") is not None and len(bundle["entry"]) >= 1


async def test_search_conditions_by_code(client: FHIRClient) -> None:
    """Searching conditions by SNOMED code 44054006 (diabetes tipo 2)."""
    bundle = await client.search("Condition", {"code": "44054006"})
    assert bundle["resourceType"] == "Bundle"
    assert bundle["total"] >= 1
    # Verify entries contain conditions with the right code
    entry = bundle["entry"][0]
    assert entry["resource"]["resourceType"] == "Condition"


async def test_search_with_count(client: FHIRClient) -> None:
    """_count parameter limits the number of returned entries."""
    bundle = await client.search("Patient", {"_count": "3"})
    assert bundle["resourceType"] == "Bundle"
    assert len(bundle["entry"]) <= 3


async def test_read_patient(client: FHIRClient) -> None:
    """Reading a specific patient by ID works."""
    # First search to get a real patient ID
    bundle = await client.search("Patient", {"_count": "1"})
    patient_id = bundle["entry"][0]["resource"]["id"]

    patient = await client.read("Patient", patient_id)
    assert patient.get_resource_type() == "Patient"
    assert patient.id == patient_id


async def test_read_nonexistent(client: FHIRClient) -> None:
    """Reading a nonexistent resource raises FHIRResourceNotFoundError."""
    with pytest.raises(FHIRResourceNotFoundError):
        await client.read("Patient", "nonexistent-id-99999")


async def test_search_empty_results(client: FHIRClient) -> None:
    """Searching with no matches returns a Bundle with total=0."""
    bundle = await client.search("Patient", {"name": "ZZZZNONEXISTENT"})
    assert bundle["resourceType"] == "Bundle"
    assert bundle["total"] == 0
    assert bundle.get("entry") is None or len(bundle["entry"]) == 0


async def test_connection_error() -> None:
    """Connecting to an unreachable server raises FHIRConnectionError."""
    config = FHIRConfig(fhir_server_url="http://localhost:19999/fhir", fhir_timeout=2.0)
    async with FHIRClient(config) as client:
        with pytest.raises(FHIRConnectionError):
            await client.check_connection()
