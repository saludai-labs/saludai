"""CLI entry point for the FHIR-AgentBench evaluation.

Usage:
    uv run python -m benchmarks.run_eval
    uv run python -m benchmarks.run_eval --category simple
    uv run python -m benchmarks.run_eval --question S01 --question M01
    uv run python -m benchmarks.run_eval --output-dir benchmarks/results
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from benchmarks.config import BenchmarkConfig
from benchmarks.dataset import load_dataset
from benchmarks.harness import EvalHarness
from benchmarks.judge import AnswerJudge
from benchmarks.metrics import compute_metrics
from benchmarks.results import print_summary, write_results_json
from saludai_agent.config import AgentConfig
from saludai_agent.llm import create_llm_client
from saludai_agent.loop import AgentLoop
from saludai_agent.tracing import create_tracer
from saludai_core.fhir_client import FHIRClient
from saludai_core.terminology import TerminologyResolver

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the SaludAI FHIR-AgentBench evaluation",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["simple", "medium", "complex"],
        help="Only run questions of this category",
    )
    parser.add_argument(
        "--question",
        type=str,
        action="append",
        dest="questions",
        help="Only run specific question IDs (can be repeated)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for result JSON files",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    """Wire dependencies and execute the benchmark."""
    load_dotenv()

    # Load configs
    agent_config = AgentConfig()
    bench_config = BenchmarkConfig()

    if args.output_dir:
        bench_config = BenchmarkConfig(output_dir=Path(args.output_dir))

    # Load and filter dataset
    questions = load_dataset(bench_config.dataset_path)

    if args.category:
        questions = [q for q in questions if q.category == args.category]
    if args.questions:
        question_ids = set(args.questions)
        questions = [q for q in questions if q.id in question_ids]

    if not questions:
        print("No questions match the given filters.")
        sys.exit(1)

    print(f"Running {len(questions)} questions...")
    print(f"Agent:  {agent_config.llm_provider}/{agent_config.llm_model}")
    print(f"Judge:  {bench_config.judge_provider}/{bench_config.judge_model}")
    print("-" * 60)

    # Create agent dependencies
    agent_llm = create_llm_client(agent_config)
    resolver = TerminologyResolver()
    tracer = create_tracer(agent_config)

    # Create judge LLM (may differ from agent LLM)
    judge_config = AgentConfig(
        llm_provider=bench_config.judge_provider,
        llm_model=bench_config.judge_model,
        llm_api_key=bench_config.judge_api_key or agent_config.llm_api_key,
    )
    judge_llm = create_llm_client(judge_config)

    async with FHIRClient() as fhir_client:
        loop = AgentLoop(
            llm=agent_llm,
            fhir_client=fhir_client,
            terminology_resolver=resolver,
            config=agent_config,
            tracer=tracer,
        )

        judge = AnswerJudge(llm=judge_llm, config=bench_config)
        harness = EvalHarness(agent_loop=loop, judge=judge, config=bench_config)

        results = await harness.run_all(questions)

    tracer.flush()

    # Compute and display metrics
    metrics = compute_metrics(results)
    print_summary(metrics)

    # Write results to JSON
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    output_path = bench_config.output_dir / f"eval_{timestamp}.json"
    config_summary = {
        "agent_provider": agent_config.llm_provider,
        "agent_model": agent_config.llm_model,
        "judge_provider": bench_config.judge_provider,
        "judge_model": bench_config.judge_model,
        "question_timeout_seconds": bench_config.question_timeout_seconds,
        "total_questions": len(questions),
    }
    write_results_json(results, metrics, config_summary, output_path)
    print(f"Results written to {output_path}")


def main() -> None:
    """Main entry point."""
    sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
