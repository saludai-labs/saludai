"""Tests for benchmarks.harness — evaluation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from benchmarks.config import BenchmarkConfig
from benchmarks.dataset import EvalQuestion
from benchmarks.harness import EvalHarness
from saludai_agent.types import AgentResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_question(qid: str = "S01", category: str = "simple") -> EvalQuestion:
    return EvalQuestion(
        id=qid,
        question="¿Cuántos pacientes hay?",
        expected_answer="200",
        category=category,  # type: ignore[arg-type]
        subcategory="count",
        requires_tools=True,
        notes="Rango: 190-210",
    )


def _make_agent_result(answer: str = "200") -> AgentResult:
    return AgentResult(
        answer=answer,
        query="¿Cuántos pacientes hay?",
        tool_calls_made=("search_fhir",),
        iterations=3,
        success=True,
        trace_id="trace-1",
    )


@dataclass(frozen=True)
class Verdict:
    score: float
    reasoning: str


def _make_config(**kwargs: Any) -> BenchmarkConfig:
    return BenchmarkConfig(
        question_timeout_seconds=kwargs.get("timeout", 300),
    )


# ---------------------------------------------------------------------------
# run_single
# ---------------------------------------------------------------------------


class TestRunSingle:
    @pytest.mark.asyncio
    async def test_correct_answer(self) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("Hay 200 pacientes.")

        judge = AsyncMock()
        judge.evaluate.return_value = Verdict(score=1.0, reasoning="correct")

        harness = EvalHarness(agent, judge, _make_config())
        result = await harness.run_single(_make_question())

        assert result.success is True
        assert result.correctness_score == 1.0
        assert result.agent_answer == "Hay 200 pacientes."
        assert result.iterations == 3

    @pytest.mark.asyncio
    async def test_incorrect_answer(self) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("No sé.")

        judge = AsyncMock()
        judge.evaluate.return_value = Verdict(score=0.0, reasoning="wrong")

        harness = EvalHarness(agent, judge, _make_config())
        result = await harness.run_single(_make_question())

        assert result.success is True
        assert result.correctness_score == 0.0

    @pytest.mark.asyncio
    async def test_timeout_returns_error_result(self) -> None:
        from unittest.mock import patch

        agent = AsyncMock()
        agent.run.return_value = _make_agent_result()

        judge = AsyncMock()
        config = _make_config()

        harness = EvalHarness(agent, judge, config)

        # Mock asyncio.wait_for to raise TimeoutError
        with patch("benchmarks.harness.asyncio.wait_for", side_effect=TimeoutError):
            result = await harness.run_single(_make_question())

        assert result.success is False
        assert "Timeout" in (result.error or "")
        assert result.correctness_score == 0.0

    @pytest.mark.asyncio
    async def test_agent_error_returns_error_result(self) -> None:
        agent = AsyncMock()
        agent.run.side_effect = RuntimeError("LLM failed")

        judge = AsyncMock()
        harness = EvalHarness(agent, judge, _make_config())
        result = await harness.run_single(_make_question())

        assert result.success is False
        assert "LLM failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_judge_error_returns_error_result(self) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("200")

        judge = AsyncMock()
        judge.evaluate.side_effect = RuntimeError("Judge broke")

        harness = EvalHarness(agent, judge, _make_config())
        result = await harness.run_single(_make_question())

        assert result.success is False
        assert "Judge error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_with_recorder(self) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("200")

        judge = AsyncMock()
        judge.evaluate.return_value = Verdict(score=1.0, reasoning="ok")

        recorder = MagicMock()
        recorder.get_recording.return_value = {
            "plan": "search patients",
            "steps": [{"iteration": 1, "tool": "search_fhir"}],
        }

        harness = EvalHarness(agent, judge, _make_config(), recorder=recorder)
        result = await harness.run_single(_make_question())

        assert result.plan == "search patients"
        assert result.steps is not None
        assert len(result.steps) == 1

    @pytest.mark.asyncio
    async def test_recorder_empty_steps(self) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("200")

        judge = AsyncMock()
        judge.evaluate.return_value = Verdict(score=1.0, reasoning="ok")

        recorder = MagicMock()
        recorder.get_recording.return_value = {"plan": None, "steps": []}

        harness = EvalHarness(agent, judge, _make_config(), recorder=recorder)
        result = await harness.run_single(_make_question())

        assert result.plan is None
        assert result.steps is None  # empty list → None


# ---------------------------------------------------------------------------
# run_all
# ---------------------------------------------------------------------------


class TestRunAll:
    @pytest.mark.asyncio
    async def test_runs_all_questions(self) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("200")

        judge = AsyncMock()
        judge.evaluate.return_value = Verdict(score=1.0, reasoning="ok")

        questions = [_make_question("S01"), _make_question("S02")]
        harness = EvalHarness(agent, judge, _make_config())
        results = await harness.run_all(questions)

        assert len(results) == 2
        assert agent.run.call_count == 2

    @pytest.mark.asyncio
    async def test_incremental_save(self, tmp_path: Path) -> None:
        agent = AsyncMock()
        agent.run.return_value = _make_agent_result("200")

        judge = AsyncMock()
        judge.evaluate.return_value = Verdict(score=1.0, reasoning="ok")

        progress = tmp_path / "progress.jsonl"
        questions = [_make_question("S01"), _make_question("S02")]
        harness = EvalHarness(agent, judge, _make_config(), progress_path=progress)
        await harness.run_all(questions)

        # Should have 2 lines in JSONL
        lines = progress.read_text().strip().split("\n")
        assert len(lines) == 2
