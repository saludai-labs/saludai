"""Evaluation result types and output utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.metrics import BenchmarkMetrics

logger = logging.getLogger(__name__)


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
        plan: Query plan from the planner (if enabled).
        steps: Per-iteration breakdown from RecordingTracer.
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
    plan: dict[str, Any] | None = None
    steps: tuple[dict[str, Any], ...] | None = None


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


def append_result_jsonl(path: Path, result: QuestionResult) -> None:
    """Append a single result as a JSON line to a JSONL file.

    Creates the file and parent directories if they don't exist.
    Each line is a self-contained JSON object, so partial files
    are always readable.

    Args:
        path: Path to the JSONL progress file.
        result: The question result to append.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(result), ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info("Progress saved: %s → %s", result.question_id, path.name)


def load_completed_ids(path: Path) -> set[str]:
    """Load question IDs already completed from a JSONL progress file.

    Skips malformed lines silently so partial files are safe to resume.

    Args:
        path: Path to the JSONL progress file.

    Returns:
        Set of question IDs that have already been evaluated.
    """
    if not path.exists():
        return set()

    completed: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            completed.add(data["question_id"])
        except (json.JSONDecodeError, KeyError):
            continue
    return completed
