"""Metrics computation for benchmark evaluation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from benchmarks.dataset import EvalQuestion
    from benchmarks.results import QuestionResult


@dataclass(frozen=True, slots=True)
class CategoryMetrics:
    """Metrics for a single question category.

    Attributes:
        total: Total questions in this category.
        correct: Number of correct answers.
        incorrect: Number of incorrect answers.
        errors: Number of questions that errored.
        accuracy: Fraction correct over total.
    """

    total: int
    correct: int
    incorrect: int
    errors: int
    accuracy: float


@dataclass(frozen=True, slots=True)
class BenchmarkMetrics:
    """Aggregated metrics for a full benchmark run.

    Attributes:
        total: Total questions evaluated.
        correct: Number of correct answers.
        incorrect: Number of incorrect answers.
        errors: Number of questions that errored.
        accuracy: Fraction correct over total (errors count as incorrect).
        accuracy_excluding_errors: Fraction correct over non-error questions.
        avg_duration_seconds: Mean wall-clock time per question.
        avg_iterations: Mean agent loop iterations per question.
        category_breakdown: Per-category metrics.
    """

    total: int
    correct: int
    incorrect: int
    errors: int
    accuracy: float
    accuracy_excluding_errors: float
    avg_duration_seconds: float
    avg_iterations: float
    category_breakdown: dict[str, CategoryMetrics] = field(default_factory=dict)


def compute_metrics(results: list[QuestionResult]) -> BenchmarkMetrics:
    """Compute aggregated metrics from a list of question results.

    Args:
        results: Per-question evaluation results.

    Returns:
        Aggregated ``BenchmarkMetrics``.
    """
    if not results:
        return BenchmarkMetrics(
            total=0,
            correct=0,
            incorrect=0,
            errors=0,
            accuracy=0.0,
            accuracy_excluding_errors=0.0,
            avg_duration_seconds=0.0,
            avg_iterations=0.0,
        )

    total = len(results)
    errors = sum(1 for r in results if not r.success)
    correct = sum(1 for r in results if r.success and r.correctness_score >= 1.0)
    incorrect = total - correct - errors

    non_error = total - errors
    accuracy = correct / total if total > 0 else 0.0
    accuracy_excl = correct / non_error if non_error > 0 else 0.0

    avg_duration = sum(r.duration_seconds for r in results) / total
    avg_iterations = sum(r.iterations for r in results) / total

    # Category breakdown
    categories: dict[str, list[QuestionResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    breakdown: dict[str, CategoryMetrics] = {}
    for cat, cat_results in categories.items():
        cat_total = len(cat_results)
        cat_errors = sum(1 for r in cat_results if not r.success)
        cat_correct = sum(1 for r in cat_results if r.success and r.correctness_score >= 1.0)
        cat_incorrect = cat_total - cat_correct - cat_errors
        breakdown[cat] = CategoryMetrics(
            total=cat_total,
            correct=cat_correct,
            incorrect=cat_incorrect,
            errors=cat_errors,
            accuracy=cat_correct / cat_total if cat_total > 0 else 0.0,
        )

    return BenchmarkMetrics(
        total=total,
        correct=correct,
        incorrect=incorrect,
        errors=errors,
        accuracy=accuracy,
        accuracy_excluding_errors=accuracy_excl,
        avg_duration_seconds=avg_duration,
        avg_iterations=avg_iterations,
        category_breakdown=breakdown,
    )


# ---------------------------------------------------------------------------
# Coverage report — dataset-level analysis (no eval run required)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Dataset coverage analysis for internal tracking and external stats.

    Attributes:
        total_questions: Total enabled questions.
        by_category: Count per difficulty category.
        by_domain: Count per clinical domain (external).
        by_graph_hops: Count per traversal depth.
        by_resource_type: Count per FHIR resource type.
        by_skill: Count per agent skill.
        resource_types_covered: Total distinct resource types.
        skills_covered: Total distinct skills.
        domains_covered: Total distinct clinical domains.
    """

    total_questions: int
    by_category: dict[str, int] = field(default_factory=dict)
    by_domain: dict[str, int] = field(default_factory=dict)
    by_graph_hops: dict[int, int] = field(default_factory=dict)
    by_resource_type: dict[str, int] = field(default_factory=dict)
    by_skill: dict[str, int] = field(default_factory=dict)
    resource_types_covered: int = 0
    skills_covered: int = 0
    domains_covered: int = 0


def compute_coverage(questions: list[EvalQuestion]) -> CoverageReport:
    """Compute dataset coverage from the question list.

    Args:
        questions: Enabled evaluation questions (already filtered).

    Returns:
        ``CoverageReport`` with breakdown by all classification dimensions.
    """
    by_category: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    by_hops: dict[int, int] = {}
    by_resource: dict[str, int] = {}
    by_skill: dict[str, int] = {}

    for q in questions:
        by_category[q.category] = by_category.get(q.category, 0) + 1
        if q.domain:
            by_domain[q.domain] = by_domain.get(q.domain, 0) + 1
        by_hops[q.graph_hops] = by_hops.get(q.graph_hops, 0) + 1
        for rt in q.resource_types:
            by_resource[rt] = by_resource.get(rt, 0) + 1
        for sk in q.skills:
            by_skill[sk] = by_skill.get(sk, 0) + 1

    return CoverageReport(
        total_questions=len(questions),
        by_category=by_category,
        by_domain=by_domain,
        by_graph_hops=by_hops,
        by_resource_type=by_resource,
        by_skill=by_skill,
        resource_types_covered=len(by_resource),
        skills_covered=len(by_skill),
        domains_covered=len(by_domain),
    )
