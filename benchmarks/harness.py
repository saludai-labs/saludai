"""Evaluation harness: orchestrates agent execution and judging."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from benchmarks.results import QuestionResult, append_result_jsonl

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.config import BenchmarkConfig
    from benchmarks.dataset import EvalQuestion
    from benchmarks.judge import AnswerJudge
    from saludai_agent.loop import AgentLoop
    from saludai_agent.tracing import RecordingTracer

logger = logging.getLogger(__name__)


class EvalHarness:
    """Orchestrates running the agent on evaluation questions and judging answers.

    Args:
        agent_loop: The configured ``AgentLoop`` to evaluate.
        judge: The ``AnswerJudge`` for scoring answers.
        config: Benchmark configuration.
        recorder: Optional ``RecordingTracer`` to capture per-iteration debug info.
        progress_path: Optional JSONL path for incremental result saving.
    """

    def __init__(
        self,
        agent_loop: AgentLoop,
        judge: AnswerJudge,
        config: BenchmarkConfig,
        recorder: RecordingTracer | None = None,
        progress_path: Path | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._agent = agent_loop
        self._judge = judge
        self._config = config
        self._recorder = recorder
        self._progress_path = progress_path
        self._delay = delay_seconds

    async def run_all(self, questions: list[EvalQuestion]) -> list[QuestionResult]:
        """Run the evaluation on all questions sequentially.

        Results are saved incrementally to JSONL if ``progress_path`` was
        provided, so partial runs survive crashes.

        Args:
            questions: List of evaluation questions to process.

        Returns:
            List of ``QuestionResult`` for each question.
        """
        results: list[QuestionResult] = []

        for i, question in enumerate(questions, 1):
            if i > 1 and self._delay > 0:
                await asyncio.sleep(self._delay)
            logger.info(
                "Evaluating question %d/%d: %s",
                i,
                len(questions),
                question.id,
            )
            result = await self.run_single(question)
            results.append(result)

            # Incremental save
            if self._progress_path is not None:
                append_result_jsonl(self._progress_path, result)

            status = "CORRECT" if result.correctness_score >= 1.0 else "INCORRECT"
            if not result.success:
                status = "ERROR"
            logger.info(
                "  [%s] %s — %.1fs, %d iterations",
                status,
                question.id,
                result.duration_seconds,
                result.iterations,
            )

        return results

    async def run_single(self, question: EvalQuestion) -> QuestionResult:
        """Run and judge a single evaluation question.

        Args:
            question: The evaluation question to process.

        Returns:
            A ``QuestionResult`` with agent answer, judge verdict, and timing.
        """
        start = time.monotonic()

        try:
            agent_result = await asyncio.wait_for(
                self._agent.run(question.question),
                timeout=self._config.question_timeout_seconds,
            )
        except TimeoutError:
            duration = time.monotonic() - start
            logger.warning("Question %s timed out after %.1fs", question.id, duration)
            return QuestionResult(
                question_id=question.id,
                question=question.question,
                expected_answer=question.expected_answer,
                agent_answer="",
                category=question.category,
                correctness_score=0.0,
                reasoning="Agent timed out",
                iterations=0,
                tool_calls_count=0,
                duration_seconds=duration,
                success=False,
                error=f"Timeout after {self._config.question_timeout_seconds}s",
            )
        except Exception as exc:
            duration = time.monotonic() - start
            logger.exception("Question %s failed with error", question.id)
            return QuestionResult(
                question_id=question.id,
                question=question.question,
                expected_answer=question.expected_answer,
                agent_answer="",
                category=question.category,
                correctness_score=0.0,
                reasoning=f"Agent error: {exc}",
                iterations=0,
                tool_calls_count=0,
                duration_seconds=duration,
                success=False,
                error=str(exc),
            )

        # Judge the answer
        try:
            verdict = await self._judge.evaluate(
                question=question.question,
                expected=question.expected_answer,
                actual=agent_result.answer,
                notes=question.notes,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            logger.exception("Judge failed for question %s", question.id)
            return QuestionResult(
                question_id=question.id,
                question=question.question,
                expected_answer=question.expected_answer,
                agent_answer=agent_result.answer,
                category=question.category,
                correctness_score=0.0,
                reasoning=f"Judge error: {exc}",
                iterations=agent_result.iterations,
                tool_calls_count=len(agent_result.tool_calls_made),
                duration_seconds=time.monotonic() - start,
                success=False,
                error=f"Judge error: {exc}",
                trace_id=agent_result.trace_id,
            )

        duration = time.monotonic() - start

        # Extract debug recording if available
        plan = None
        steps = None
        total_input_tokens = 0
        total_output_tokens = 0
        if self._recorder is not None:
            recording = self._recorder.get_recording()
            plan = recording.get("plan")
            raw_steps = recording.get("steps")
            if raw_steps:
                steps = tuple(raw_steps)
                for step in raw_steps:
                    usage = step.get("usage", {})
                    total_input_tokens += usage.get("input_tokens", 0)
                    total_output_tokens += usage.get("output_tokens", 0)

        return QuestionResult(
            question_id=question.id,
            question=question.question,
            expected_answer=question.expected_answer,
            agent_answer=agent_result.answer,
            category=question.category,
            correctness_score=verdict.score,
            reasoning=verdict.reasoning,
            iterations=agent_result.iterations,
            tool_calls_count=len(agent_result.tool_calls_made),
            duration_seconds=duration,
            success=True,
            trace_id=agent_result.trace_id,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            plan=plan,
            steps=steps,
        )
