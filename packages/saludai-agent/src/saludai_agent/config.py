"""Agent configuration via pydantic-settings.

Settings are loaded from environment variables with the ``SALUDAI_`` prefix,
matching the convention established in ``saludai_core.config``.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    """Configuration for the SaludAI agent loop.

    Attributes:
        llm_provider: LLM backend to use.
        llm_model: Model identifier.
        llm_api_key: API key for anthropic/openai providers.
        llm_base_url: Base URL override (required for ollama).
        agent_max_iterations: Maximum tool-calling loop iterations.
        agent_max_tokens: Max tokens for LLM responses.
        agent_temperature: Sampling temperature (0.0 for deterministic).
        langfuse_enabled: Enable Langfuse tracing (requires env vars).
    """

    model_config = SettingsConfigDict(env_prefix="SALUDAI_", extra="ignore")

    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    agent_max_iterations: int = 8
    agent_max_tokens: int = 4096
    agent_temperature: float = 0.0
    langfuse_enabled: bool = False
