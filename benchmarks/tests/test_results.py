"""Tests for the results output module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from benchmarks.metrics import BenchmarkMetrics, CategoryMetrics, compute_metrics
from benchmarks.results import (
    QuestionResult,
    append_result_jsonl,
    load_completed_ids,
    print_summary,
    write_results_json,
)

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


# ---------------------------------------------------------------------------
# TestQuestionResultNewFields
# ---------------------------------------------------------------------------


class TestQuestionResultNewFields:
    """QuestionResult supports optional plan and steps fields."""

    def test_defaults_to_none(self) -> None:
        result = _make_result()
        assert result.plan is None
        assert result.steps is None

    def test_with_plan_and_steps(self) -> None:
        plan = {"strategy": "count_simple", "model": "haiku"}
        steps = (
            {"iteration": 1, "llm_output": "searching", "tool_calls": [], "usage": {}},
        )
        result = _make_result()
        # Create new instance since frozen
        result = QuestionResult(
            question_id="T01",
            question="test?",
            expected_answer="expected",
            agent_answer="actual",
            category="simple",
            correctness_score=1.0,
            reasoning="ok",
            iterations=1,
            tool_calls_count=0,
            duration_seconds=1.0,
            success=True,
            plan=plan,
            steps=steps,
        )
        assert result.plan == plan
        assert len(result.steps) == 1

    def test_serializes_with_asdict(self) -> None:
        from dataclasses import asdict

        plan = {"strategy": "count_simple"}
        steps = ({"iteration": 1, "tool_calls": [{"name": "search_fhir"}]},)
        result = QuestionResult(
            question_id="T01",
            question="test?",
            expected_answer="42",
            agent_answer="42",
            category="simple",
            correctness_score=1.0,
            reasoning="ok",
            iterations=1,
            tool_calls_count=0,
            duration_seconds=1.0,
            success=True,
            plan=plan,
            steps=steps,
        )
        d = asdict(result)
        assert d["plan"] == plan
        assert d["steps"] == steps
        # Ensure JSON-serializable
        json.dumps(d, default=str)


# ---------------------------------------------------------------------------
# TestAppendResultJsonl
# ---------------------------------------------------------------------------


class TestAppendResultJsonl:
    """Tests for incremental JSONL saving."""

    def test_creates_file_and_appends(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.jsonl"
        r1 = _make_result(question_id="S01")
        r2 = _make_result(question_id="S02")

        append_result_jsonl(path, r1)
        append_result_jsonl(path, r2)

        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["question_id"] == "S01"
        assert json.loads(lines[1])["question_id"] == "S02"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "progress.jsonl"
        append_result_jsonl(path, _make_result())
        assert path.exists()

    def test_preserves_utf8(self, tmp_path: Path) -> None:
        path = tmp_path / "utf8.jsonl"
        result = QuestionResult(
            question_id="T01",
            question="¿Cuántos pacientes?",
            expected_answer="55",
            agent_answer="55 pacientes",
            category="simple",
            correctness_score=1.0,
            reasoning="Correcto",
            iterations=1,
            tool_calls_count=0,
            duration_seconds=1.0,
            success=True,
        )
        append_result_jsonl(path, result)
        text = path.read_text(encoding="utf-8")
        assert "¿Cuántos" in text


# ---------------------------------------------------------------------------
# TestLoadCompletedIds
# ---------------------------------------------------------------------------


class TestLoadCompletedIds:
    """Tests for loading completed question IDs from JSONL."""

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.jsonl"
        assert load_completed_ids(path) == set()

    def test_loads_ids_from_jsonl(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.jsonl"
        append_result_jsonl(path, _make_result(question_id="S01"))
        append_result_jsonl(path, _make_result(question_id="M05"))
        append_result_jsonl(path, _make_result(question_id="C10"))

        ids = load_completed_ids(path)
        assert ids == {"S01", "M05", "C10"}

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.jsonl"
        path.write_text(
            '{"question_id": "S01"}\n'
            "not valid json\n"
            '{"no_id_field": true}\n'
            '{"question_id": "S02"}\n',
            encoding="utf-8",
        )
        ids = load_completed_ids(path)
        assert ids == {"S01", "S02"}

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "empty_lines.jsonl"
        path.write_text(
            '{"question_id": "S01"}\n\n\n{"question_id": "S02"}\n',
            encoding="utf-8",
        )
        ids = load_completed_ids(path)
        assert ids == {"S01", "S02"}
