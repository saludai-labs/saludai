"""Benchmark configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BenchmarkConfig(BaseSettings):
    """Configuration for the FHIR-AgentBench evaluation harness.

    All settings can be overridden via ``SALUDAI_BENCH_*`` environment variables.
    """

    model_config = SettingsConfigDict(env_prefix="SALUDAI_BENCH_", extra="ignore")

    # Judge LLM settings
    judge_provider: str = "anthropic"
    judge_model: str = "claude-haiku-4-5-20251001"
    judge_api_key: str | None = None

    # Execution settings
    question_timeout_seconds: int = 300

    # Paths
    dataset_path: Path = Path(__file__).parent / "dataset.json"
    output_dir: Path = Path(__file__).parent / "results"

    # Filters (optional)
    categories: list[str] | None = None
    question_ids: list[str] | None = None
