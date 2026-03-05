"""Tests for the SaludAI REST API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from saludai_agent.types import AgentResult
from saludai_api.app import app


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
