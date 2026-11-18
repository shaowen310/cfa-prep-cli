"""
CFA Prep CLI - Tests for the mistake store module
Author: CodeBuddy AI Assistant
Purpose: Check the SQLite store of the mistake log: writing, reading, the counts
         and the export to JSON.
"""

import json
import sqlite3
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


def test_mistake_store_question_key():
    """Test that a question is found whatever the punctuation at its end is"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        store.upsert(_record("What is demand?"))

        # The same question, typed with another closing punctuation or spacing
        assert len(store.load_by_question("What is demand?")) == 1
        assert len(store.load_by_question("what is demand:")) == 1
        assert len(store.load_by_question("  WHAT IS DEMAND  ")) == 1
        # Another question is not found
        assert len(store.load_by_question("What is a quota?")) == 0
        print("  ✅ A question is found whatever the punctuation at its end is")


def test_mistake_store_migrates_old_database():
    """Test that an older database gets the matching key and stays searchable"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = root / "mistakes.db"
        # A database of the shape it had before the matching key existed
        connection = sqlite3.connect(db)
        _ = connection.execute(
            """CREATE TABLE mistakes (
                question_id TEXT PRIMARY KEY,
                date TEXT NOT NULL DEFAULT '',
                last_date TEXT NOT NULL DEFAULT '',
                attempts INTEGER NOT NULL DEFAULT 1,
                level TEXT NOT NULL DEFAULT '',
                subject TEXT NOT NULL DEFAULT '',
                "module" TEXT NOT NULL DEFAULT '',
                question TEXT NOT NULL DEFAULT '',
                options TEXT NOT NULL DEFAULT '[]',
                user_answer TEXT NOT NULL DEFAULT '',
                correct_answer TEXT NOT NULL DEFAULT '',
                explanation TEXT NOT NULL DEFAULT '',
                wrong_answers TEXT NOT NULL DEFAULT '[]',
                table_json TEXT
            )"""
        )
        _ = connection.execute(
            "INSERT INTO mistakes (question_id, question) VALUES (?, ?)",
            ("q:old", "What is demand?"),
        )
        connection.commit()
        connection.close()

        store = MistakeStore(db)
        assert store.count() == 1, store.count()
        found = store.load_by_question("what is demand:")
        assert len(found) == 1, found
        print("  ✅ An older database gets the matching key and stays searchable")


def test_mistake_store_merge_duplicates():
    """Test that a question that is logged twice ends up in a single row"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        first = _record("What is demand?")
        store.upsert(first)
        # The same question, logged again under a slightly different text
        second = _record("What is demand:")
        second["question_id"] = "q:other"
        second["attempts"] = 1
        second["wrong_answers"] = ["C"]
        store.upsert(second)
        assert store.count() == 2, store.count()

        # The group shows what would be merged
        groups = store.duplicate_groups()
        assert len(groups) == 1, groups
        assert len(groups[0]) == 2, groups

        removed = store.merge_duplicates()
        assert removed == 1, removed
        assert store.count() == 1, store.count()
        merged = store.load_by_question("what is demand")
        assert len(merged) == 1, merged
        assert merged[0].get("attempts") == 2, merged
        assert merged[0].get("wrong_answers") == ["C"], merged
        print("  ✅ A question that is logged twice ends up in a single row")


def test_mistake_store_merge_keeps_the_hand_written_content():
    """Test that the merge keeps the explanation of the newest row"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        first = _record("What is demand?")
        first["explanation"] = ""
        first["user_answer"] = ""
        store.upsert(first)
        # The question is logged again and the explanation is typed in
        second = _record("What is demand:")
        second["question_id"] = "q:other"
        second["explanation"] = "Because of the reason."
        second["user_answer"] = "C"
        store.upsert(second)

        assert store.merge_duplicates() == 1
        merged = store.load_by_question("what is demand")
        assert len(merged) == 1, merged
        assert merged[0].get("explanation") == "Because of the reason.", merged
        assert merged[0].get("user_answer") == "C", merged
        # The oldest row is the one that is kept
        assert merged[0]["question_id"] == first["question_id"], merged
        print("  ✅ The merge keeps the explanation that was typed in")


def test_mistake_store_merge_writes_the_texts_carefully():
    """Test that the merge keeps the punctuation and capitalises the sentences"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        # The first record: no punctuation, a lower case sentence
        first = _record("What is demand")
        first["options"] = ["A tariff", "An import quota", "A restraint"]
        first["user_answer"] = "A tariff"
        first["correct_answer"] = "An import quota"
        first["explanation"] = "the demand falls when the price rises."
        store.upsert(first)
        # The same question, written with the punctuation and in upper case
        second = _record("What is demand:")
        second["question_id"] = "q:other"
        second["options"] = ["An import quota.", "A restraint.", "A tariff."]
        second["user_answer"] = "A tariff."
        second["correct_answer"] = "An import quota."
        second["explanation"] = "The demand falls when the price rises."
        store.upsert(second)

        assert store.merge_duplicates() == 1
        merged = store.load_by_question("what is demand")
        assert len(merged) == 1, merged
        record = merged[0]
        # The question that ends with punctuation is kept
        assert record["question"] == "What is demand:", record
        # The options keep their punctuation, in the order of the newest row
        assert record.get("options") == [
            "An import quota.",
            "A restraint.",
            "A tariff.",
        ], record
        # The answers are written the way the options they belong to are
        assert record.get("user_answer") == "A tariff.", record
        assert record.get("correct_answer") == "An import quota.", record
        # The sentence starts with a capital letter
        assert (
            record.get("explanation") == "The demand falls when the price rises."
        ), record
        print("  ✅ The merge keeps the punctuation and capitalises the sentences")


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
