"""Evaluation result types and output utilities."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.metrics import BenchmarkMetrics


@dataclass(frozen=True, slots=True)
class QuestionResult:
    """Result of evaluating a single question.

    Attributes:
        question_id: Unique identifier from the dataset.
        question: The natural-language question.
        expected_answer: Gold-standard answer.
        agent_answer: The agent's actual answer.
        category: Question difficulty category.
        correctness_score: Binary score from the judge (0.0 or 1.0).
        reasoning: Judge's explanation for the verdict.
        iterations: Number of agent loop iterations.
        tool_calls_count: Number of tool calls the agent made.
        duration_seconds: Wall-clock time to process the question.
        success: Whether the agent completed without errors.
        error: Error message if the agent or judge failed.
        trace_id: Langfuse trace ID (if tracing enabled).
    """

    question_id: str
    question: str
    expected_answer: str
    agent_answer: str
    category: str
    correctness_score: float
    reasoning: str
    iterations: int
    tool_calls_count: int
    duration_seconds: float
    success: bool
    error: str | None = None
    trace_id: str | None = None


def write_results_json(
    results: list[QuestionResult],
    metrics: BenchmarkMetrics,
    config_summary: dict[str, Any],
    path: Path,
) -> None:
    """Write evaluation results and metrics to a JSON file.

    Args:
        results: Per-question results.
        metrics: Aggregated metrics.
        config_summary: Configuration snapshot for reproducibility.
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "config": config_summary,
        "metrics": asdict(metrics),
        "results": [asdict(r) for r in results],
    }

    path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def print_summary(metrics: BenchmarkMetrics) -> None:
    """Print a human-readable summary of benchmark metrics to stdout."""
    print("\n" + "=" * 60)
    print("  FHIR-AgentBench — SaludAI Evaluation Results")
    print("=" * 60)
    print(f"  Total questions:         {metrics.total}")
    print(f"  Correct:                 {metrics.correct}")
    print(f"  Incorrect:               {metrics.incorrect}")
    print(f"  Errors:                  {metrics.errors}")
    print(f"  Accuracy:                {metrics.accuracy:.1%}")
    print(f"  Accuracy (excl. errors): {metrics.accuracy_excluding_errors:.1%}")
    print(f"  Avg duration:            {metrics.avg_duration_seconds:.1f}s")
    print(f"  Avg iterations:          {metrics.avg_iterations:.1f}")
    print("-" * 60)

    if metrics.category_breakdown:
        print("  Category Breakdown:")
        for cat, cat_metrics in sorted(metrics.category_breakdown.items()):
            acc = f"{cat_metrics.accuracy:.0%}"
            print(f"    {cat:10s}  {cat_metrics.correct}/{cat_metrics.total}  ({acc})")

    print("=" * 60 + "\n")
