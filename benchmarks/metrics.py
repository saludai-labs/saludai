"""Metrics computation for benchmark evaluation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
