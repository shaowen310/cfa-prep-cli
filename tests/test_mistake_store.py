"""
CFA Prep CLI - Tests for the mistake store module
Author: CodeBuddy AI Assistant
Purpose: Check the SQLite store of the mistake log: writing, reading, the counts
         and the import of the old JSON log.
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


def test_mistake_store_migration():
    """Test that the old JSON log is imported once and then kept as a backup"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        legacy = root / "mistakes.json"
        _ = legacy.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "date": "20260101",
                            "level": "L1",
                            "subject": "Economics",
                            "module": "Module 1: Basics",
                            "question": "What is demand?",
                            "question_id": "q:dem",
                            "options": ["A", "B"],
                            "user_answer": "A",
                            "correct_answer": "B",
                            "explanation": "",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        store = MistakeStore(root / "mistakes.db", legacy)
        imported = store.import_legacy()
        assert imported == 1, imported
        assert store.count() == 1, store.count()
        # The old file is kept as a backup
        assert not legacy.exists()
        backup = root / "mistakes.json.imported"
        assert backup.is_file(), backup
        assert json.loads(backup.read_text(encoding="utf-8"))["records"]

        # A second import does not touch the log that is in use
        store.upsert(_record("What is a quota?"))
        assert store.import_legacy() == 0
        assert store.count() == 2, store.count()
        print("  ✅ The old JSON log is imported once and then kept as a backup")


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
