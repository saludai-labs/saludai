"""Evaluation result types and output utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.metrics import BenchmarkMetrics, DistributionStats

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
    total_input_tokens: int = 0
    total_output_tokens: int = 0
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


def _fmt_dist(label: str, stats: DistributionStats, unit: str = "") -> str:
    """Format a distribution stats line."""
    u = unit
    return (
        f"    {label:18s}  "
        f"avg={stats.mean:6.1f}{u}  "
        f"p50={stats.median:6.1f}{u}  "
        f"p75={stats.p75:6.1f}{u}  "
        f"p90={stats.p90:6.1f}{u}  "
        f"p95={stats.p95:6.1f}{u}"
    )


def _fmt_dist_int(label: str, stats: DistributionStats) -> str:
    """Format a distribution stats line for integer values."""
    return (
        f"    {label:18s}  "
        f"avg={stats.mean:5.1f}  "
        f"p50={stats.median:5.0f}  "
        f"p75={stats.p75:5.0f}  "
        f"p90={stats.p90:5.0f}  "
        f"p95={stats.p95:5.0f}"
    )


def _fmt_token_dist(label: str, stats: DistributionStats) -> str:
    """Format a distribution stats line for token counts (in K)."""
    return (
        f"    {label:18s}  "
        f"avg={stats.mean / 1000:5.1f}K  "
        f"p50={stats.median / 1000:5.1f}K  "
        f"p75={stats.p75 / 1000:5.1f}K  "
        f"p90={stats.p90 / 1000:5.1f}K  "
        f"p95={stats.p95 / 1000:5.1f}K"
    )


def print_summary(metrics: BenchmarkMetrics) -> None:
    """Print a human-readable summary of benchmark metrics to stdout."""
    print("\n" + "=" * 70)
    print("  FHIR-AgentBench — SaludAI Evaluation Results")
    print("=" * 70)
    print(f"  Total questions:         {metrics.total}")
    print(f"  Correct:                 {metrics.correct}")
    print(f"  Incorrect:               {metrics.incorrect}")
    print(f"  Errors:                  {metrics.errors}")
    print(f"  Accuracy:                {metrics.accuracy:.1%}")
    print(f"  Accuracy (excl. errors): {metrics.accuracy_excluding_errors:.1%}")
    print("-" * 70)

    if metrics.category_breakdown:
        print("  Category Breakdown:")
        for cat, cat_metrics in sorted(metrics.category_breakdown.items()):
            acc = f"{cat_metrics.accuracy:.0%}"
            err = f"  ({cat_metrics.errors} err)" if cat_metrics.errors else ""
            print(f"    {cat:10s}  {cat_metrics.correct}/{cat_metrics.total}  ({acc}){err}")
        print("-" * 70)

    # Distribution tables
    print("  Distribution Stats:          avg    p50    p75    p90    p95")
    if metrics.duration_stats:
        print(_fmt_dist("Duration (s)", metrics.duration_stats, "s"))
    if metrics.iteration_stats:
        print(_fmt_dist_int("Iterations", metrics.iteration_stats))
    if metrics.tool_calls_stats:
        print(_fmt_dist_int("Tool calls", metrics.tool_calls_stats))
    print("-" * 70)

    # Token usage
    total_tokens = metrics.total_input_tokens + metrics.total_output_tokens
    if total_tokens > 0:
        in_tok = metrics.total_input_tokens
        out_tok = metrics.total_output_tokens
        n = metrics.total
        print("  Token Usage:")
        print(f"    Total:     {total_tokens:,} ({in_tok:,} in + {out_tok:,} out)")
        avg_in, avg_out = in_tok // n, out_tok // n
        print(f"    Per query: {avg_in + avg_out:,} avg ({avg_in:,} in + {avg_out:,} out)")
        if metrics.input_token_stats:
            print(_fmt_token_dist("Input tokens", metrics.input_token_stats))
        if metrics.output_token_stats:
            print(_fmt_token_dist("Output tokens", metrics.output_token_stats))

    print("=" * 70 + "\n")


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
