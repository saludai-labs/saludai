"""LLM-as-judge for binary correctness evaluation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from benchmarks.config import BenchmarkConfig
    from saludai_agent.llm import LLMClient

logger = logging.getLogger(__name__)

# Regex patterns for extracting numeric ranges from notes
_RANGE_PATTERNS = [
    # "Aceptar entre 83% y 93%", "aceptar entre 13 y 17"
    re.compile(r"[Aa]ceptar\s+entre\s+([\d.,]+)%?\s+y\s+([\d.,]+)"),
    # "Rango aceptable: 13-17", "rango: 13-17"
    re.compile(r"[Rr]ango[^:]*:\s*([\d.,]+)\s*[-\u2013]\s*([\d.,]+)"),
    # "entre 83% y 93%", "entre 13 y 17"
    re.compile(r"entre\s+([\d.,]+)%?\s+y\s+([\d.,]+)"),
    # Bare "58-66" or "58\u201366" (no prefix needed)
    re.compile(r"(\d+(?:[.,]\d+)?)\s*[-\u2013]\s*(\d+(?:[.,]\d+)?)"),
]

# Regex to find numbers in agent answer
_NUMBER_RE = re.compile(r"(\d+(?:[.,]\d+)?)")

_JUDGE_SYSTEM_PROMPT = """\
You are a strict but fair evaluator of a healthcare FHIR agent.
You will receive:
- A question about clinical data
- The expected (gold) answer
- The agent's actual answer
- Optional notes with acceptable ranges or criteria

Your task: determine if the agent's answer is CORRECT or INCORRECT.

Rules:
- CORRECT: The agent's answer contains the key factual information.
  Formatting differences, extra details, or different wording are acceptable.
  IMPORTANT: If the notes specify an acceptable numeric range (e.g. "Aceptar entre 13 y 17"),
  any number within that range is CORRECT, even if it differs from the expected answer.
  The notes field takes PRIORITY over the expected answer for determining correctness.
- INCORRECT: The agent's answer is factually wrong, gives a number outside the acceptable range,
  missing key information, or the agent failed to answer the question.
- If the agent says it encountered an error or couldn't find data, mark as INCORRECT.
- Be tolerant of format differences but strict on factual accuracy.
- Always check the notes for acceptable ranges before deciding.

Respond ONLY with a JSON object (no markdown, no extra text):
{"verdict": "CORRECT" or "INCORRECT", "reasoning": "brief explanation"}
"""

_JUDGE_USER_TEMPLATE = """\
Question: {question}

Expected answer: {expected}

Agent's answer: {actual}

Notes: {notes}
"""


@dataclass(frozen=True, slots=True)
class JudgeVerdict:
    """Result of the LLM judge evaluation.

    Attributes:
        correct: Whether the answer was judged correct.
        score: Binary score (1.0 for correct, 0.0 for incorrect).
        reasoning: The judge's explanation.
    """

    correct: bool
    score: float
    reasoning: str


class AnswerJudge:
    """Evaluates agent answers using an LLM as judge."""

    def __init__(self, llm: LLMClient, config: BenchmarkConfig) -> None:
        self._llm = llm
        self._config = config

    async def evaluate(
        self,
        question: str,
        expected: str,
        actual: str,
        notes: str = "",
    ) -> JudgeVerdict:
        """Evaluate an agent answer against the expected answer.

        Args:
            question: The original question.
            expected: The gold-standard expected answer.
            actual: The agent's actual answer.
            notes: Extra context for the judge.

        Returns:
            A ``JudgeVerdict`` with correctness and reasoning.
        """
        # Fast-path: programmatic range check when notes specify a numeric range.
        # This is more reliable (and cheaper) than asking an LLM to compare numbers.
        if notes:
            range_verdict = self._check_numeric_range(actual, notes)
            if range_verdict is not None:
                return range_verdict

        from saludai_agent.types import Message

        user_prompt = _JUDGE_USER_TEMPLATE.format(
            question=question,
            expected=expected,
            actual=actual,
            notes=notes or "None",
        )

        response = await self._llm.generate(
            system=_JUDGE_SYSTEM_PROMPT,
            messages=[Message(role="user", content=user_prompt)],
            tools=None,
            temperature=0.0,
            max_tokens=512,
        )

        return self._parse_verdict(response.content or "")

    @staticmethod
    def _check_numeric_range(actual: str, notes: str) -> JudgeVerdict | None:
        """Check if the agent's answer falls within a numeric range from notes.

        Returns a ``JudgeVerdict`` if a range was found and a number extracted
        from the answer, or ``None`` to fall through to the LLM judge.
        """
        # Extract range from notes
        lo: float | None = None
        hi: float | None = None
        for pattern in _RANGE_PATTERNS:
            m = pattern.search(notes)
            if m:
                try:
                    lo = float(m.group(1).replace(",", "."))
                    hi = float(m.group(2).replace(",", "."))
                except ValueError:
                    continue
                break

        if lo is None or hi is None:
            return None  # No numeric range found — fall through to LLM

        # Extract numbers from the agent's answer
        numbers = _NUMBER_RE.findall(actual)
        if not numbers:
            return None  # No numbers in answer — let LLM judge

        # Check if ANY number in the answer falls within the range
        for num_str in numbers:
            try:
                num = float(num_str.replace(",", "."))
            except ValueError:
                continue
            if lo <= num <= hi:
                return JudgeVerdict(
                    correct=True,
                    score=1.0,
                    reasoning=f"Programmatic range check: {num} is within [{lo}, {hi}]",
                )

        # Numbers found but none in range — mark incorrect
        found = [n for n in numbers]
        return JudgeVerdict(
            correct=False,
            score=0.0,
            reasoning=f"Programmatic range check: found {found}, none within [{lo}, {hi}]",
        )

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove markdown code fences (```json ... ```) if present."""
        stripped = text.strip()
        if stripped.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        return stripped.strip()

    @staticmethod
    def _parse_verdict(raw: str) -> JudgeVerdict:
        """Parse the judge's JSON response into a ``JudgeVerdict``.

        Falls back to INCORRECT if parsing fails.
        """
        try:
            cleaned = AnswerJudge._strip_markdown_fences(raw)
            data = json.loads(cleaned)
            verdict = str(data.get("verdict", "")).upper()
            reasoning = str(data.get("reasoning", ""))
            correct = verdict == "CORRECT"
            return JudgeVerdict(
                correct=correct,
                score=1.0 if correct else 0.0,
                reasoning=reasoning,
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            logger.warning("Failed to parse judge response: %s", raw[:200])
            return JudgeVerdict(
                correct=False,
                score=0.0,
                reasoning=f"Failed to parse judge response: {raw[:200]}",
            )
