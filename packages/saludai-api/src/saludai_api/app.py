"""SaludAI REST API — FastAPI application with /query endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from saludai_agent.config import AgentConfig
from saludai_agent.llm import create_llm_client
from saludai_agent.loop import AgentLoop
from saludai_agent.tracing import create_tracer
from saludai_core.config import FHIRConfig
from saludai_core.fhir_client import FHIRClient
from saludai_core.locales import load_locale_pack
from saludai_core.terminology import TerminologyResolver

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_fhir_client: FHIRClient | None = None
_agent_loop: AgentLoop | None = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialise agent dependencies on startup, tear down on shutdown."""
    global _fhir_client, _agent_loop

    agent_cfg = AgentConfig()
    fhir_cfg = FHIRConfig()

    _fhir_client = FHIRClient(config=fhir_cfg)

    try:
        locale_pack = load_locale_pack(agent_cfg.locale)
    except Exception:
        locale_pack = None
        logger.warning("locale_pack_not_found", locale=agent_cfg.locale)

    terminology = TerminologyResolver(locale_pack=locale_pack)
    llm = create_llm_client(agent_cfg)
    tracer = create_tracer(agent_cfg)

    _agent_loop = AgentLoop(
        llm=llm,
        fhir_client=_fhir_client,
        terminology_resolver=terminology,
        config=agent_cfg,
        tracer=tracer,
        locale_pack=locale_pack,
    )

    logger.info(
        "api_started",
        fhir_server=fhir_cfg.fhir_server_url,
        llm_provider=agent_cfg.llm_provider,
        llm_model=agent_cfg.llm_model,
    )

    try:
        yield
    finally:
        await _fhir_client.close()
        _fhir_client = None
        _agent_loop = None
        logger.info("api_stopped")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SaludAI",
    description="The most precise FHIR agent for Latin America. "
    "Ask clinical questions in natural language and get answers from FHIR R4 servers.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Natural language query to the FHIR agent."""

    question: str = Field(
        ...,
        description="Clinical question in natural language (Spanish or English).",
        examples=["¿Cuántos pacientes con diabetes tipo 2 hay mayores de 60?"],
    )


class QueryResponse(BaseModel):
    """Agent response with answer and metadata."""

    answer: str = Field(description="Narrative answer from the agent.")
    question: str = Field(description="Original question.")
    iterations: int = Field(description="Number of agent loop iterations.")
    tool_calls_made: int = Field(description="Total tool calls executed.")
    trace_id: str | None = Field(default=None, description="Langfuse trace ID.")
    trace_url: str | None = Field(default=None, description="Langfuse trace URL.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Ask a clinical question and get an answer from the FHIR agent."""
    if _agent_loop is None:
        raise HTTPException(status_code=503, detail="Agent not initialised.")

    try:
        result = await _agent_loop.run(request.question)
    except Exception as exc:
        logger.error("query_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        answer=result.answer,
        question=result.query,
        iterations=result.iterations,
        tool_calls_made=len(result.tool_calls_made),
        trace_id=result.trace_id,
        trace_url=result.trace_url,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
