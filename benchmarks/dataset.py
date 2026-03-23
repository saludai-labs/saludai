"""Evaluation dataset: questions, expected answers, and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class EvalQuestion:
    """A single evaluation question with its expected answer.

    Attributes:
        id: Unique question identifier (e.g. ``"S01"``).
        question: Natural-language question in Spanish.
        expected_answer: Gold-standard answer for the judge.
        category: Difficulty level.
        subcategory: Finer classification of what the question tests.
        requires_tools: Whether the agent needs tool calls to answer.
        notes: Extra context for the LLM judge (e.g. acceptable ranges).
        enabled: Whether the question is active in evaluations.
        resource_types: FHIR resource types exercised (internal tracking).
        graph_hops: Graph traversal depth — 0=single, 1=hub-spoke, 2+=multi-hop.
        skills: Agent capabilities tested (internal tracking).
        domain: Clinical domain for external reporting.
    """

    id: str
    question: str
    expected_answer: str
    category: Literal["simple", "medium", "complex"]
    subcategory: str
    requires_tools: bool
    notes: str = ""
    enabled: bool = True
    resource_types: tuple[str, ...] = ()
    graph_hops: int = 0
    skills: tuple[str, ...] = ()
    domain: str = ""


def load_dataset(path: Path | str | None = None) -> list[EvalQuestion]:
    """Load and validate the evaluation dataset from a JSON file.

    Args:
        path: Path to the dataset JSON. Defaults to ``dataset.json``
              in the same directory as this module.

    Returns:
        List of validated ``EvalQuestion`` instances.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        ValueError: If the dataset is empty or has duplicate IDs.
    """
    if path is None:
        path = Path(__file__).parent / "dataset.json"
    path = Path(path)

    raw = json.loads(path.read_text(encoding="utf-8"))

    if not raw:
        msg = f"Dataset at {path} is empty"
        raise ValueError(msg)

    questions = []
    for item in raw:
        # Convert JSON arrays to tuples for frozen dataclass fields.
        for key in ("resource_types", "skills"):
            if key in item and isinstance(item[key], list):
                item[key] = tuple(item[key])
        questions.append(EvalQuestion(**item))
    questions = [q for q in questions if q.enabled]

    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        duplicates = [qid for qid in ids if ids.count(qid) > 1]
        msg = f"Duplicate question IDs: {set(duplicates)}"
        raise ValueError(msg)

    return questions
