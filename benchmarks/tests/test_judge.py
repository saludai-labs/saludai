"""Tests for the LLM-as-judge module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from benchmarks.config import BenchmarkConfig
from benchmarks.judge import AnswerJudge, JudgeVerdict


def _make_judge_llm(response_content: str) -> Any:
    """Create a mock LLM that returns the given content."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=MagicMock(content=response_content))
    return llm


class TestJudgeVerdict:
    """Tests for the JudgeVerdict dataclass."""

    def test_correct_verdict(self) -> None:
        v = JudgeVerdict(correct=True, score=1.0, reasoning="Matches expected.")
        assert v.correct is True
        assert v.score == 1.0

    def test_incorrect_verdict(self) -> None:
        v = JudgeVerdict(correct=False, score=0.0, reasoning="Wrong answer.")
        assert v.correct is False
        assert v.score == 0.0


class TestAnswerJudge:
    """Tests for the AnswerJudge class."""

    @pytest.mark.asyncio
    async def test_correct_evaluation(self) -> None:
        llm = _make_judge_llm('{"verdict": "CORRECT", "reasoning": "Good answer."}')
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        verdict = await judge.evaluate(
            question="¿Cuántos pacientes hay?",
            expected="55",
            actual="Hay 55 pacientes.",
        )
        assert verdict.correct is True
        assert verdict.score == 1.0
        assert "Good answer" in verdict.reasoning

    @pytest.mark.asyncio
    async def test_incorrect_evaluation(self) -> None:
        llm = _make_judge_llm('{"verdict": "INCORRECT", "reasoning": "Wrong number."}')
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        verdict = await judge.evaluate(
            question="¿Cuántos pacientes hay?",
            expected="55",
            actual="Hay 100 pacientes.",
        )
        assert verdict.correct is False
        assert verdict.score == 0.0

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back_to_incorrect(self) -> None:
        llm = _make_judge_llm("this is not json")
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        verdict = await judge.evaluate(
            question="test",
            expected="expected",
            actual="actual",
        )
        assert verdict.correct is False
        assert verdict.score == 0.0
        assert "Failed to parse" in verdict.reasoning

    @pytest.mark.asyncio
    async def test_empty_response_falls_back_to_incorrect(self) -> None:
        llm = _make_judge_llm("")
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        verdict = await judge.evaluate(
            question="test",
            expected="expected",
            actual="actual",
        )
        assert verdict.correct is False

    @pytest.mark.asyncio
    async def test_notes_passed_to_llm(self) -> None:
        llm = _make_judge_llm('{"verdict": "CORRECT", "reasoning": "ok"}')
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        await judge.evaluate(
            question="test",
            expected="expected",
            actual="actual",
            notes="Accept any number > 5",
        )

        # Verify the notes were included in the message
        call_kwargs = llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages", [])
        assert any("Accept any number > 5" in (m.content or "") for m in messages)

    @pytest.mark.asyncio
    async def test_lowercase_verdict_accepted(self) -> None:
        llm = _make_judge_llm('{"verdict": "correct", "reasoning": "ok"}')
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        verdict = await judge.evaluate(
            question="test",
            expected="expected",
            actual="actual",
        )
        assert verdict.correct is True


class TestNumericRangeCheck:
    """Tests for the programmatic numeric range pre-check."""

    def test_within_range_aceptar(self) -> None:
        v = AnswerJudge._check_numeric_range(
            "Hay 16 pacientes con diabetes tipo 2.",
            "Aceptar entre 13 y 17",
        )
        assert v is not None
        assert v.correct is True

    def test_outside_range(self) -> None:
        v = AnswerJudge._check_numeric_range(
            "Encontré 50 pacientes.",
            "Aceptar entre 13 y 17",
        )
        assert v is not None
        assert v.correct is False

    def test_no_range_in_notes(self) -> None:
        v = AnswerJudge._check_numeric_range(
            "Hay 16 pacientes.",
            "El valor exacto es 15",
        )
        assert v is None  # Falls through to LLM

    def test_no_number_in_answer(self) -> None:
        v = AnswerJudge._check_numeric_range(
            "No pude encontrar datos.",
            "Aceptar entre 13 y 17",
        )
        assert v is None  # Falls through to LLM

    def test_range_with_rango_keyword(self) -> None:
        v = AnswerJudge._check_numeric_range(
            "El resultado es 22.",
            "Rango aceptable: 20-25",
        )
        assert v is not None
        assert v.correct is True

    def test_range_with_entre_keyword(self) -> None:
        v = AnswerJudge._check_numeric_range(
            "Son 5 pacientes.",
            "entre 3 y 8",
        )
        assert v is not None
        assert v.correct is True

    def test_boundary_values(self) -> None:
        """Exact boundary values should be accepted."""
        v_lo = AnswerJudge._check_numeric_range("13", "Aceptar entre 13 y 17")
        v_hi = AnswerJudge._check_numeric_range("17", "Aceptar entre 13 y 17")
        assert v_lo is not None and v_lo.correct is True
        assert v_hi is not None and v_hi.correct is True

    @pytest.mark.asyncio
    async def test_range_bypasses_llm(self) -> None:
        """When a numeric range matches, the LLM should NOT be called."""
        llm = _make_judge_llm('{"verdict": "INCORRECT", "reasoning": "wrong"}')
        config = BenchmarkConfig()
        judge = AnswerJudge(llm=llm, config=config)

        verdict = await judge.evaluate(
            question="¿Cuántos pacientes con DM2?",
            expected="15",
            actual="Hay 16 pacientes con diabetes tipo 2.",
            notes="Aceptar entre 13 y 17",
        )
        assert verdict.correct is True
        llm.generate.assert_not_called()  # LLM was never invoked
