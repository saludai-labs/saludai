"""Tests for the SaludAI REST API."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from saludai_agent.types import AgentResult
from saludai_api.app import app, lifespan

# saludai_api re-exports `app` which shadows the module; use sys.modules
_app_module = sys.modules["saludai_api.app"]


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client without lifespan (we mock the agent)."""
    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestQueryEndpoint:
    """Tests for POST /query."""

    def test_query_returns_agent_result(self, client: TestClient) -> None:
        mock_result = AgentResult(
            answer="Hay 14 pacientes con diabetes tipo 2 mayores de 60.",
            query="¿Cuántos pacientes con diabetes tipo 2 hay mayores de 60?",
            tool_calls_made=(),
            iterations=3,
            success=True,
            trace_id="trace-123",
            trace_url="https://langfuse.example.com/trace/123",
        )

        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result

        with patch("saludai_api.app._agent_loop", mock_agent):
            response = client.post(
                "/query",
                json={"question": "¿Cuántos pacientes con diabetes tipo 2 hay mayores de 60?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Hay 14 pacientes con diabetes tipo 2 mayores de 60."
        assert data["question"] == "¿Cuántos pacientes con diabetes tipo 2 hay mayores de 60?"
        assert data["iterations"] == 3
        assert data["trace_id"] == "trace-123"

    def test_query_without_question_returns_422(self, client: TestClient) -> None:
        response = client.post("/query", json={})
        assert response.status_code == 422

    def test_query_when_agent_not_initialised_returns_503(self, client: TestClient) -> None:
        with patch("saludai_api.app._agent_loop", None):
            response = client.post(
                "/query",
                json={"question": "test"},
            )
        assert response.status_code == 503

    def test_query_when_agent_errors_returns_500(self, client: TestClient) -> None:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("LLM timeout")

        with patch("saludai_api.app._agent_loop", mock_agent):
            response = client.post(
                "/query",
                json={"question": "test"},
            )
        assert response.status_code == 500


class TestLifespan:
    """Tests for the lifespan context manager (startup/shutdown)."""

    @pytest.mark.asyncio
    async def test_lifespan_initialises_and_tears_down(self) -> None:
        """Lifespan creates agent loop on startup and cleans up on shutdown."""
        mock_fhir_client = AsyncMock()
        mock_llm = MagicMock()
        mock_tracer = MagicMock()
        mock_agent_loop = MagicMock()

        with (
            patch("saludai_api.app.FHIRClient", return_value=mock_fhir_client),
            patch("saludai_api.app.create_llm_client", return_value=mock_llm),
            patch("saludai_api.app.create_tracer", return_value=mock_tracer),
            patch("saludai_api.app.AgentLoop", return_value=mock_agent_loop),
            patch("saludai_api.app.load_locale_pack", return_value=None),
        ):
            async with lifespan(app):
                # During lifespan, agent loop should be set
                assert _app_module._agent_loop is mock_agent_loop
                assert _app_module._fhir_client is mock_fhir_client

        # After lifespan, everything cleaned up
        assert _app_module._fhir_client is None
        assert _app_module._agent_loop is None
        mock_fhir_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_handles_locale_not_found(self) -> None:
        """Lifespan continues even if locale pack is not found."""
        mock_fhir_client = AsyncMock()

        with (
            patch("saludai_api.app.FHIRClient", return_value=mock_fhir_client),
            patch("saludai_api.app.create_llm_client"),
            patch("saludai_api.app.create_tracer"),
            patch("saludai_api.app.AgentLoop"),
            patch("saludai_api.app.load_locale_pack", side_effect=Exception("not found")),
        ):
            async with lifespan(app):
                pass  # Should not raise


class TestOpenAPISchema:
    """Verify OpenAPI docs are generated correctly."""

    def test_openapi_schema_has_query_endpoint(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/query" in schema["paths"]
        assert "post" in schema["paths"]["/query"]

    def test_openapi_schema_has_health_endpoint(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/health" in schema["paths"]
