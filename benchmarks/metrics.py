"""Metrics computation for benchmark evaluation results."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from benchmarks.dataset import EvalQuestion
    from benchmarks.results import QuestionResult


# ---------------------------------------------------------------------------
# Distribution statistics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DistributionStats:
    """Descriptive statistics for a numeric distribution.

    Attributes:
        count: Number of data points.
        mean: Arithmetic mean.
        median: 50th percentile.
        p75: 75th percentile.
        p90: 90th percentile.
        p95: 95th percentile.
        stdev: Sample standard deviation (0.0 if count < 2).
        min: Minimum value.
        max: Maximum value.
    """

    count: int
    mean: float
    median: float
    p75: float
    p90: float
    p95: float
    stdev: float
    min: float
    max: float


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute percentile using linear interpolation (same as numpy default)."""
    n = len(sorted_values)
    k = (n - 1) * p / 100.0
    f = int(k)
    c = f + 1
    if c >= n:
        return sorted_values[-1]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def compute_distribution(values: list[float]) -> DistributionStats:
    """Compute distribution statistics from a list of values.

    Args:
        values: Numeric values to analyze.

    Returns:
        ``DistributionStats`` with mean, median, percentiles, and spread.
    """
    if not values:
        return DistributionStats(
            count=0, mean=0.0, median=0.0, p75=0.0, p90=0.0,
            p95=0.0, stdev=0.0, min=0.0, max=0.0,
        )
    sorted_vals = sorted(values)
    return DistributionStats(
        count=len(values),
        mean=statistics.mean(values),
        median=statistics.median(values),
        p75=_percentile(sorted_vals, 75),
        p90=_percentile(sorted_vals, 90),
        p95=_percentile(sorted_vals, 95),
        stdev=statistics.stdev(values) if len(values) > 1 else 0.0,
        min=sorted_vals[0],
        max=sorted_vals[-1],
    )


# ---------------------------------------------------------------------------
# Category metrics
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Benchmark metrics
# ---------------------------------------------------------------------------


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
        duration_stats: Distribution of wall-clock time per question.
        iteration_stats: Distribution of agent loop iterations per question.
        tool_calls_stats: Distribution of tool calls per question.
        total_input_tokens: Sum of input tokens across all questions.
        total_output_tokens: Sum of output tokens across all questions.
        input_token_stats: Distribution of input tokens per question.
        output_token_stats: Distribution of output tokens per question.
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
    duration_stats: DistributionStats | None = None
    iteration_stats: DistributionStats | None = None
    tool_calls_stats: DistributionStats | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    input_token_stats: DistributionStats | None = None
    output_token_stats: DistributionStats | None = None


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

    # Distribution stats
    durations = [r.duration_seconds for r in results]
    iterations = [float(r.iterations) for r in results]
    tool_calls = [float(r.tool_calls_count) for r in results]
    input_tokens = [float(r.total_input_tokens) for r in results]
    output_tokens = [float(r.total_output_tokens) for r in results]

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
        duration_stats=compute_distribution(durations),
        iteration_stats=compute_distribution(iterations),
        tool_calls_stats=compute_distribution(tool_calls),
        total_input_tokens=sum(r.total_input_tokens for r in results),
        total_output_tokens=sum(r.total_output_tokens for r in results),
        input_token_stats=compute_distribution(input_tokens),
        output_token_stats=compute_distribution(output_tokens),
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
