"""Tests for the evaluation dataset module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from benchmarks.dataset import EvalQuestion, load_dataset


class TestEvalQuestion:
    """Tests for the EvalQuestion dataclass."""

    def test_create_eval_question(self) -> None:
        q = EvalQuestion(
            id="T01",
            question="test?",
            expected_answer="yes",
            category="simple",
            subcategory="count",
            requires_tools=True,
        )
        assert q.id == "T01"
        assert q.category == "simple"
        assert q.notes == ""

    def test_eval_question_is_frozen(self) -> None:
        q = EvalQuestion(
            id="T01",
            question="test?",
            expected_answer="yes",
            category="simple",
            subcategory="count",
            requires_tools=True,
        )
        with pytest.raises(AttributeError):
            q.id = "T02"  # type: ignore[misc]


class TestLoadDataset:
    """Tests for the load_dataset function."""

    def test_load_real_dataset(self) -> None:
        questions = load_dataset()
        assert len(questions) == 50

    def test_all_ids_unique(self) -> None:
        questions = load_dataset()
        ids = [q.id for q in questions]
        assert len(ids) == len(set(ids))

    def test_all_categories_present(self) -> None:
        questions = load_dataset()
        categories = {q.category for q in questions}
        assert categories == {"simple", "medium", "complex"}

    def test_all_fields_non_empty(self) -> None:
        questions = load_dataset()
        for q in questions:
            assert q.id, f"Empty id in {q}"
            assert q.question, f"Empty question in {q}"
            assert q.expected_answer, f"Empty expected_answer in {q}"
            assert q.subcategory, f"Empty subcategory in {q}"

    def test_load_from_custom_path(self, tmp_path: Path) -> None:
        data = [
            {
                "id": "X01",
                "question": "¿Cuántos?",
                "expected_answer": "5",
                "category": "simple",
                "subcategory": "count",
                "requires_tools": False,
            }
        ]
        path = tmp_path / "test_dataset.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        questions = load_dataset(path)
        assert len(questions) == 1
        assert questions[0].id == "X01"

    def test_empty_dataset_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            load_dataset(path)

    def test_duplicate_ids_raises(self, tmp_path: Path) -> None:
        data = [
            {
                "id": "DUP",
                "question": "q1",
                "expected_answer": "a1",
                "category": "simple",
                "subcategory": "count",
                "requires_tools": False,
            },
            {
                "id": "DUP",
                "question": "q2",
                "expected_answer": "a2",
                "category": "simple",
                "subcategory": "count",
                "requires_tools": False,
            },
        ]
        path = tmp_path / "dup.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="Duplicate"):
            load_dataset(path)
