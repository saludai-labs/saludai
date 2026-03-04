"""Tests for the results output module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from benchmarks.metrics import BenchmarkMetrics, CategoryMetrics, compute_metrics
from benchmarks.results import QuestionResult, print_summary, write_results_json

if TYPE_CHECKING:
    from pathlib import Path


def _make_result(
    *,
    question_id: str = "T01",
    category: str = "simple",
    correctness_score: float = 1.0,
    success: bool = True,
) -> QuestionResult:
    return QuestionResult(
        question_id=question_id,
        question="test?",
        expected_answer="expected",
        agent_answer="actual",
        category=category,
        correctness_score=correctness_score,
        reasoning="test reasoning",
        iterations=2,
        tool_calls_count=1,
        duration_seconds=3.5,
        success=success,
    )


class TestWriteResultsJson:
    """Tests for write_results_json."""

    def test_creates_output_file(self, tmp_path: Path) -> None:
        results = [_make_result()]
        metrics = compute_metrics(results)
        output = tmp_path / "results" / "test.json"

        write_results_json(results, metrics, {"model": "test"}, output)

        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["config"]["model"] == "test"
        assert data["metrics"]["total"] == 1
        assert len(data["results"]) == 1

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        output = tmp_path / "deep" / "nested" / "dir" / "results.json"
        results = [_make_result()]
        metrics = compute_metrics(results)

        write_results_json(results, metrics, {}, output)
        assert output.exists()

    def test_utf8_content_preserved(self, tmp_path: Path) -> None:
        result = QuestionResult(
            question_id="T01",
            question="¿Cuántos pacientes?",
            expected_answer="55 pacientes",
            agent_answer="Hay 55 pacientes en el sistema",
            category="simple",
            correctness_score=1.0,
            reasoning="Correcto",
            iterations=1,
            tool_calls_count=0,
            duration_seconds=1.0,
            success=True,
        )
        metrics = compute_metrics([result])
        output = tmp_path / "utf8.json"

        write_results_json([result], metrics, {}, output)

        text = output.read_text(encoding="utf-8")
        assert "¿Cuántos" in text
        assert "\\u" not in text  # ensure_ascii=False


class TestPrintSummary:
    """Tests for print_summary."""

    def test_prints_without_error(self, capsys: object) -> None:
        metrics = BenchmarkMetrics(
            total=10,
            correct=7,
            incorrect=2,
            errors=1,
            accuracy=0.7,
            accuracy_excluding_errors=0.778,
            avg_duration_seconds=5.2,
            avg_iterations=2.5,
            category_breakdown={
                "simple": CategoryMetrics(total=4, correct=4, incorrect=0, errors=0, accuracy=1.0),
            },
        )
        # Should not raise
        print_summary(metrics)
