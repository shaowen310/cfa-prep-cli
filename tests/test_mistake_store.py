"""
CFA Prep CLI - Tests for the mistake store module
Author: CodeBuddy AI Assistant
Purpose: Check the SQLite store of the mistake log: writing, reading, the counts
         and the export to JSON.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.mistake_store import MistakeRecord, MistakeStore


def _record(question: str, module: str = "Module 1: Basics") -> MistakeRecord:
    """Build a record for the tests."""
    return MistakeRecord(
        date="20261118",
        level="L1",
        subject="Economics",
        module=module,
        question=question,
        question_id=f"q:{question}",
        options=["A", "B", "C"],
        user_answer="A",
        correct_answer="B",
        explanation="Because of the reason.",
    )


def test_mistake_store_upsert():
    """Test that a record is written, updated and counted"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        assert store.count() == 0

        record = _record("What is demand?")
        store.upsert(record)
        assert store.count() == 1

        # The same question id updates the row instead of adding one
        record["attempts"] = 2
        record["user_answer"] = "C"
        store.upsert(record)
        assert store.count() == 1
        stored = store.get(record["question_id"])
        assert stored is not None
        assert stored.get("attempts") == 2, stored
        assert stored.get("user_answer") == "C", stored
        assert stored.get("options") == ["A", "B", "C"], stored
        print("  ✅ A record is written, updated and counted")


def test_mistake_store_queries():
    """Test that the log can be read by subject, module, question and date"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        store.upsert(_record("What is demand?"))
        store.upsert(_record("What is a quota?", "Module 6: International Trade"))
        store.upsert(_record("What is duration?", "Module 6: International Trade"))

        assert len(store.load_all()) == 3
        found = store.load_by_subject_module(
            "Economics", "Module 6: International Trade"
        )
        assert len(found) == 2, found
        assert len(store.load_by_question("what is demand?")) == 1
        assert len(store.load_recent(2)) == 2

        # The counts come from the database
        groups = store.grouped_counts()
        assert len(groups) == 2, groups
        total = sum(questions for _s, _m, questions, _a in groups)
        assert total == 3, groups
        print("  ✅ The log can be read by subject, module, question and date")


def test_mistake_store_export():
    """Test that the log can be written as a JSON file again"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = MistakeStore(root / "mistakes.db")
        store.upsert(_record("What is demand?"))

        target = root / "export.json"
        store.export_json(target)
        data = json.loads(target.read_text(encoding="utf-8"))
        assert len(data["records"]) == 1, data
        assert data["records"][0]["question"] == "What is demand?", data
        # No half-written file is left behind
        assert not (root / "export.json.tmp").exists()
        print("  ✅ The log can be written as a JSON file again")
