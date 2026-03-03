"""Tests for saludai_agent.config."""

from __future__ import annotations

import pytest

from saludai_agent.config import AgentConfig


class TestAgentConfigDefaults:
    """Default values match the plan."""

    def test_default_provider(self) -> None:
        config = AgentConfig()
        assert config.llm_provider == "anthropic"

    def test_default_model(self) -> None:
        config = AgentConfig()
        assert config.llm_model == "claude-sonnet-4-20250514"

    def test_default_api_key_is_none(self) -> None:
        config = AgentConfig()
        assert config.llm_api_key is None

    def test_default_base_url_is_none(self) -> None:
        config = AgentConfig()
        assert config.llm_base_url is None

    def test_default_max_iterations(self) -> None:
        config = AgentConfig()
        assert config.agent_max_iterations == 5

    def test_default_max_tokens(self) -> None:
        config = AgentConfig()
        assert config.agent_max_tokens == 4096

    def test_default_temperature(self) -> None:
        config = AgentConfig()
        assert config.agent_temperature == 0.0


class TestAgentConfigEnvVars:
    """Config is loaded from environment variables with SALUDAI_ prefix."""

    def test_env_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_LLM_PROVIDER", "openai")
        config = AgentConfig()
        assert config.llm_provider == "openai"

    def test_env_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_LLM_MODEL", "gpt-4o")
        config = AgentConfig()
        assert config.llm_model == "gpt-4o"

    def test_env_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_LLM_API_KEY", "sk-test-123")
        config = AgentConfig()
        assert config.llm_api_key == "sk-test-123"

    def test_env_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_LLM_BASE_URL", "http://localhost:11434/v1")
        config = AgentConfig()
        assert config.llm_base_url == "http://localhost:11434/v1"

    def test_env_max_iterations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_AGENT_MAX_ITERATIONS", "10")
        config = AgentConfig()
        assert config.agent_max_iterations == 10

    def test_env_max_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_AGENT_MAX_TOKENS", "8192")
        config = AgentConfig()
        assert config.agent_max_tokens == 8192

    def test_env_temperature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SALUDAI_AGENT_TEMPERATURE", "0.5")
        config = AgentConfig()
        assert config.agent_temperature == 0.5


class TestAgentConfigValidation:
    """Config validates provider literals."""

    def test_invalid_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Input should be"):
            AgentConfig(llm_provider="invalid")  # type: ignore[arg-type]

    def test_ollama_provider_is_valid(self) -> None:
        config = AgentConfig(llm_provider="ollama")
        assert config.llm_provider == "ollama"

    def test_explicit_construction(self) -> None:
        config = AgentConfig(
            llm_provider="openai",
            llm_model="gpt-4o",
            llm_api_key="sk-test",
            agent_max_iterations=3,
        )
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o"
        assert config.llm_api_key == "sk-test"
        assert config.agent_max_iterations == 3
