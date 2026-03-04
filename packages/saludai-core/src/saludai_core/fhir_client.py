"""Async FHIR R4 client backed by httpx.

Provides ``check_connection``, ``read``, and ``search`` operations against a
FHIR R4 server.  All responses are parsed into ``fhir.resources`` Pydantic
models for type safety.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType

import httpx
import structlog

from saludai_core.config import FHIRConfig
from saludai_core.exceptions import (
    FHIRAuthenticationError,
    FHIRConnectionError,
    FHIRResourceNotFoundError,
    FHIRValidationError,
)

logger = structlog.get_logger(__name__)


def _get_resource_class(resource_type: str) -> type[Any]:
    """Import and return the ``fhir.resources`` class for *resource_type*.

    Args:
        resource_type: FHIR resource type name, e.g. ``"Patient"``.

    Returns:
        The Pydantic model class for the given FHIR resource.

    Raises:
        FHIRValidationError: If the resource type is unknown.
    """
    try:
        module = importlib.import_module(f"fhir.resources.{resource_type.lower()}")
        return getattr(module, resource_type)  # type: ignore[no-any-return]
    except (ModuleNotFoundError, AttributeError) as exc:
        raise FHIRValidationError(f"Unknown FHIR resource type: {resource_type}") from exc


class FHIRClient:
    """Async FHIR R4 client.

    Args:
        config: FHIR connection settings.  Defaults are loaded from
            environment variables when *config* is ``None``.

    Example::

        async with FHIRClient() as client:
            cap = await client.check_connection()
            bundle = await client.search("Patient", {"name": "Garcia"})
    """

    def __init__(self, config: FHIRConfig | None = None) -> None:
        self._config = config or FHIRConfig()

        headers: dict[str, str] = {
            "Accept": "application/fhir+json",
        }
        if self._config.fhir_auth_type == "bearer" and self._config.fhir_auth_token:
            headers["Authorization"] = f"Bearer {self._config.fhir_auth_token}"

        self._http = httpx.AsyncClient(
            base_url=self._config.fhir_server_url,
            headers=headers,
            timeout=self._config.fhir_timeout,
        )
        self._log = logger.bind(fhir_server=self._config.fhir_server_url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_connection(self) -> Any:
        """Fetch the server's ``CapabilityStatement`` and verify FHIR R4.

        Returns:
            A ``fhir.resources.capabilitystatement.CapabilityStatement``.

        Raises:
            FHIRConnectionError: If the server is unreachable.
            FHIRValidationError: If the response is not valid FHIR R4.
        """
        self._log.info("fhir.check_connection")
        data = await self._request("GET", "/metadata")
        try:
            cls = _get_resource_class("CapabilityStatement")
            capability = cls.model_validate(data)
        except Exception as exc:
            raise FHIRValidationError("Invalid CapabilityStatement from FHIR server") from exc

        fhir_version = getattr(capability, "fhirVersion", None)
        if fhir_version and not str(fhir_version).startswith("4."):
            raise FHIRValidationError(
                f"Expected FHIR R4 but server reported version {fhir_version}"
            )

        self._log.info("fhir.connected", fhir_version=str(fhir_version))
        return capability

    async def read(self, resource_type: str, resource_id: str) -> Any:
        """Read a single FHIR resource by type and id.

        Args:
            resource_type: FHIR resource type, e.g. ``"Patient"``.
            resource_id: Logical id of the resource.

        Returns:
            A typed ``fhir.resources`` model instance.

        Raises:
            FHIRResourceNotFoundError: If the resource does not exist (404).
            FHIRConnectionError: If the server is unreachable.
            FHIRValidationError: If the response cannot be parsed.
        """
        self._log.info("fhir.read", resource_type=resource_type, resource_id=resource_id)
        data = await self._request("GET", f"/{resource_type}/{resource_id}")
        return self._parse_resource(resource_type, data)

    async def read_raw(self, resource_type: str, resource_id: str) -> dict[str, Any]:
        """Read a single FHIR resource and return the raw JSON dict.

        Unlike ``read()``, this skips ``fhir.resources`` Pydantic parsing,
        avoiding issues with strict ``extra="forbid"`` on choice-type fields.

        Args:
            resource_type: FHIR resource type, e.g. ``"Patient"``.
            resource_id: Logical id of the resource.

        Returns:
            The raw JSON dict from the FHIR server.

        Raises:
            FHIRResourceNotFoundError: If the resource does not exist (404).
            FHIRConnectionError: If the server is unreachable.
        """
        self._log.info("fhir.read_raw", resource_type=resource_type, resource_id=resource_id)
        return await self._request("GET", f"/{resource_type}/{resource_id}")

    async def search(
        self,
        resource_type: str,
        params: dict[str, str | list[str]] | None = None,
    ) -> dict[str, Any]:
        """Search for FHIR resources.

        Args:
            resource_type: FHIR resource type to search, e.g. ``"Patient"``.
            params: Query parameters as a dict.  Values may be strings or
                lists of strings for repeated parameters.

        Returns:
            The raw FHIR Bundle as a dict.  We intentionally skip
            ``fhir.resources`` validation here because its strict
            Pydantic v2 models reject valid FHIR choice-type fields
            (e.g. ``medicationCodeableConcept`` in MedicationRequest).

        Raises:
            FHIRConnectionError: If the server is unreachable.
        """
        self._log.info("fhir.search", resource_type=resource_type, params=params)
        query_params = self._build_query_params(params)
        return await self._request("GET", f"/{resource_type}", params=query_params)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._log.debug("fhir.client_closed")

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> FHIRClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request and return the parsed JSON body.

        Raises:
            FHIRConnectionError: On network errors.
            FHIRAuthenticationError: On 401/403.
            FHIRResourceNotFoundError: On 404.
            FHIRValidationError: On unexpected status codes or invalid JSON.
        """
        try:
            response = await self._http.request(method, path, params=params)
        except httpx.ConnectError as exc:
            raise FHIRConnectionError(
                f"Cannot connect to FHIR server at {self._config.fhir_server_url}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise FHIRConnectionError(
                f"Timeout connecting to FHIR server at {self._config.fhir_server_url}"
            ) from exc

        if response.status_code in (401, 403):
            raise FHIRAuthenticationError(f"Authentication failed (HTTP {response.status_code})")
        if response.status_code == 404:
            raise FHIRResourceNotFoundError(f"Resource not found: {method} {path}")
        if response.status_code >= 400:
            raise FHIRValidationError(
                f"FHIR server returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError as exc:
            raise FHIRValidationError("FHIR server returned non-JSON response") from exc

    @staticmethod
    def _build_query_params(
        params: dict[str, str | list[str]] | None,
    ) -> list[tuple[str, str]] | None:
        """Flatten *params* dict into a list of ``(key, value)`` tuples.

        This correctly handles repeated parameters (e.g. multiple ``_include``).
        """
        if not params:
            return None
        result: list[tuple[str, str]] = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    result.append((key, v))
            else:
                result.append((key, value))
        return result

    @staticmethod
    def _parse_resource(resource_type: str, data: dict[str, Any]) -> Any:
        """Parse a JSON dict into the appropriate ``fhir.resources`` model."""
        cls = _get_resource_class(resource_type)
        try:
            return cls.model_validate(data)
        except Exception as exc:
            raise FHIRValidationError(f"Failed to parse {resource_type}: {exc}") from exc
