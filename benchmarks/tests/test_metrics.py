"""Tests for the metrics computation module."""

from __future__ import annotations

import pytest

from benchmarks.dataset import EvalQuestion
from benchmarks.metrics import compute_coverage, compute_metrics
from benchmarks.results import QuestionResult


def _make_result(
    *,
    question_id: str = "T01",
    category: str = "simple",
    correctness_score: float = 1.0,
    success: bool = True,
    duration_seconds: float = 5.0,
    iterations: int = 2,
    error: str | None = None,
) -> QuestionResult:
    """Helper to create a QuestionResult with minimal boilerplate."""
    return QuestionResult(
        question_id=question_id,
        question="test question",
        expected_answer="expected",
        agent_answer="actual",
        category=category,
        correctness_score=correctness_score,
        reasoning="test",
        iterations=iterations,
        tool_calls_count=1,
        duration_seconds=duration_seconds,
        success=success,
        error=error,
    )


class TestComputeMetrics:
    """Tests for compute_metrics."""

    def test_empty_results(self) -> None:
        m = compute_metrics([])
        assert m.total == 0
        assert m.accuracy == 0.0
        assert m.avg_duration_seconds == 0.0

    def test_all_correct(self) -> None:
        results = [
            _make_result(question_id="Q1", correctness_score=1.0),
            _make_result(question_id="Q2", correctness_score=1.0),
            _make_result(question_id="Q3", correctness_score=1.0),
        ]
        m = compute_metrics(results)
        assert m.total == 3
        assert m.correct == 3
        assert m.incorrect == 0
        assert m.errors == 0
        assert m.accuracy == pytest.approx(1.0)
        assert m.accuracy_excluding_errors == pytest.approx(1.0)

    def test_all_incorrect(self) -> None:
        results = [
            _make_result(question_id="Q1", correctness_score=0.0),
            _make_result(question_id="Q2", correctness_score=0.0),
        ]
        m = compute_metrics(results)
        assert m.total == 2
        assert m.correct == 0
        assert m.incorrect == 2
        assert m.accuracy == pytest.approx(0.0)

    def test_mixed_results(self) -> None:
        results = [
            _make_result(question_id="Q1", correctness_score=1.0),
            _make_result(question_id="Q2", correctness_score=0.0),
            _make_result(question_id="Q3", correctness_score=1.0),
            _make_result(question_id="Q4", correctness_score=0.0),
        ]
        m = compute_metrics(results)
        assert m.total == 4
        assert m.correct == 2
        assert m.incorrect == 2
        assert m.accuracy == pytest.approx(0.5)

    def test_with_errors(self) -> None:
        results = [
            _make_result(question_id="Q1", correctness_score=1.0),
            _make_result(question_id="Q2", success=False, correctness_score=0.0, error="timeout"),
            _make_result(question_id="Q3", correctness_score=0.0),
        ]
        m = compute_metrics(results)
        assert m.total == 3
        assert m.correct == 1
        assert m.errors == 1
        assert m.incorrect == 1
        assert m.accuracy == pytest.approx(1 / 3)
        assert m.accuracy_excluding_errors == pytest.approx(0.5)

    def test_avg_duration(self) -> None:
        results = [
            _make_result(question_id="Q1", duration_seconds=2.0),
            _make_result(question_id="Q2", duration_seconds=4.0),
            _make_result(question_id="Q3", duration_seconds=6.0),
        ]
        m = compute_metrics(results)
        assert m.avg_duration_seconds == pytest.approx(4.0)

    def test_avg_iterations(self) -> None:
        results = [
            _make_result(question_id="Q1", iterations=1),
            _make_result(question_id="Q2", iterations=3),
            _make_result(question_id="Q3", iterations=5),
        ]
        m = compute_metrics(results)
        assert m.avg_iterations == pytest.approx(3.0)

    def test_category_breakdown(self) -> None:
        results = [
            _make_result(question_id="Q1", category="simple", correctness_score=1.0),
            _make_result(question_id="Q2", category="simple", correctness_score=1.0),
            _make_result(question_id="Q3", category="medium", correctness_score=0.0),
            _make_result(question_id="Q4", category="complex", correctness_score=1.0),
        ]
        m = compute_metrics(results)
        assert "simple" in m.category_breakdown
        assert "medium" in m.category_breakdown
        assert "complex" in m.category_breakdown
        assert m.category_breakdown["simple"].correct == 2
        assert m.category_breakdown["simple"].accuracy == pytest.approx(1.0)
        assert m.category_breakdown["medium"].correct == 0
        assert m.category_breakdown["complex"].correct == 1

    def test_all_errors(self) -> None:
        results = [
            _make_result(question_id="Q1", success=False, correctness_score=0.0, error="err"),
            _make_result(question_id="Q2", success=False, correctness_score=0.0, error="err"),
        ]
        m = compute_metrics(results)
        assert m.errors == 2
        assert m.correct == 0
        assert m.accuracy == pytest.approx(0.0)
        assert m.accuracy_excluding_errors == pytest.approx(0.0)


def _make_question(
    *,
    qid: str = "T01",
    category: str = "simple",
    resource_types: tuple[str, ...] = ("Patient",),
    graph_hops: int = 0,
    skills: tuple[str, ...] = ("counting",),
    domain: str = "demographics",
) -> EvalQuestion:
    return EvalQuestion(
        id=qid,
        question="test?",
        expected_answer="yes",
        category=category,
        subcategory="test",
        requires_tools=True,
        resource_types=resource_types,
        graph_hops=graph_hops,
        skills=skills,
        domain=domain,
    )


class TestComputeCoverage:
    """Tests for compute_coverage."""

    def test_empty(self) -> None:
        c = compute_coverage([])
        assert c.total_questions == 0
        assert c.resource_types_covered == 0

    def test_single_question(self) -> None:
        c = compute_coverage([_make_question()])
        assert c.total_questions == 1
        assert c.by_category == {"simple": 1}
        assert c.by_domain == {"demographics": 1}
        assert c.by_graph_hops == {0: 1}
        assert c.by_resource_type == {"Patient": 1}
        assert c.by_skill == {"counting": 1}
        assert c.resource_types_covered == 1
        assert c.skills_covered == 1
        assert c.domains_covered == 1

    def test_multiple_questions(self) -> None:
        qs = [
            _make_question(
                qid="Q1",
                resource_types=("Patient", "Condition"),
                skills=("terminology", "counting"),
                domain="chronic_disease",
                graph_hops=1,
            ),
            _make_question(
                qid="Q2",
                category="complex",
                resource_types=("Patient", "Condition", "Observation"),
                skills=("cross_resource",),
                domain="laboratory",
                graph_hops=2,
            ),
        ]
        c = compute_coverage(qs)
        assert c.total_questions == 2
        assert c.resource_types_covered == 3
        assert c.by_resource_type["Patient"] == 2
        assert c.by_resource_type["Condition"] == 2
        assert c.by_resource_type["Observation"] == 1
        assert c.domains_covered == 2
        assert c.by_graph_hops == {1: 1, 2: 1}

    def test_real_dataset(self) -> None:
        from benchmarks.dataset import load_dataset

        questions = load_dataset()
        c = compute_coverage(questions)
        assert c.total_questions >= 100
        assert c.resource_types_covered == 10
        assert c.skills_covered == 10
        assert c.domains_covered == 9
