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
from typing import cast

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
        correct_answer="B",
        explanation="Because of the reason.",
        wrong_answers=["A"],
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
        record["wrong_answers"] = ["C"]
        store.upsert(record)
        assert store.count() == 1
        stored = store.get(record["question_id"])
        assert stored is not None
        assert stored.get("attempts") == 2, stored
        assert stored.get("wrong_answers") == ["C"], stored
        assert stored.get("options") == ["A", "B", "C"], stored
        print("  ✅ A record is written, updated and counted")


def test_mistake_store_keeps_the_wrong_answer_in_the_history():
    """Test that the wrong answer is only kept in the history"""
    import sqlite3

    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        store.upsert(_record("What is demand?"))

        connection = sqlite3.connect(store.db_path)
        connection.row_factory = sqlite3.Row
        columns = [
            cast(str, row[1])
            for row in cast(
                list[sqlite3.Row],
                connection.execute("PRAGMA table_info(mistakes)").fetchall(),
            )
        ]
        connection.close()
        # The answer that was given wrong has no column of its own
        assert "user_answer" not in columns, columns
        assert "wrong_answers" in columns, columns

        stored = store.get("q:What is demand?")
        assert stored is not None
        assert stored.get("wrong_answers") == ["A"], stored
        print("  ✅ The wrong answer is only kept in the history")


def test_mistake_store_separates_the_same_question_from_another_one():
    """Test that a question with other options is not a duplicate"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        # The same question, logged twice under a different text
        first = _record("What is demand?")
        first["question_id"] = "q:first"
        store.upsert(first)
        second = _record("What is demand:")
        second["question_id"] = "q:second"
        store.upsert(second)
        # Another question that is written the same way
        other = _record("What is demand?")
        other["question_id"] = "q:other"
        other["options"] = ["D", "E", "F"]
        other["correct_answer"] = "E"
        other["wrong_answers"] = ["D"]
        store.upsert(other)

        # The two rows with the same options are a duplicate
        duplicates = store.duplicate_groups()
        assert len(duplicates) == 1, duplicates
        assert len(duplicates[0]) == 2, duplicates
        # The question with the other options is not one of them
        assert store.similar_groups(), store.similar_groups()
        similar = store.similar_groups()[0]
        assert len(similar) == 3, similar

        # Only the duplicate is merged
        assert store.merge_duplicates() == 1
        assert store.count() == 2, store.count()
        print("  ✅ A question with other options is not a duplicate")


def test_mistake_store_clears_the_wrong_answers_when_the_answer_changes():
    """Test that the wrong answers are cleared when the correct answer changes"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        first = _record("What is demand?")
        first["question_id"] = "q:first"
        first["correct_answer"] = "A"
        first["wrong_answers"] = ["B"]
        store.upsert(first)
        second = _record("What is demand:")
        second["question_id"] = "q:second"
        second["correct_answer"] = "C"
        second["wrong_answers"] = ["B"]
        store.upsert(second)

        groups = store.duplicate_groups()
        assert len(groups) == 1, groups
        # The reader chooses the other answer
        store.merge_group(groups[0], "C")
        stored = store.get("q:first")
        assert stored is not None
        assert stored.get("correct_answer") == "C", stored
        # The wrong answers belonged to the answer of before
        assert not stored.get("wrong_answers"), stored
        print("  ✅ The wrong answers are cleared when the answer changes")


def test_mistake_store_keeps_the_wrong_answers_when_the_answer_stays():
    """Test that the wrong answers stay when the correct answer does not change"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        first = _record("What is demand?")
        first["question_id"] = "q:first"
        first["wrong_answers"] = ["C"]
        store.upsert(first)
        second = _record("What is demand:")
        second["question_id"] = "q:second"
        second["wrong_answers"] = ["A"]
        store.upsert(second)

        groups = store.duplicate_groups()
        assert len(groups) == 1, groups
        store.merge_group(groups[0])
        stored = store.get("q:first")
        assert stored is not None
        assert stored.get("wrong_answers") == ["C", "A"], stored
        print("  ✅ The wrong answers stay when the answer does not change")


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
        # Both wrong answers are kept: they are two different traps
        assert merged[0].get("wrong_answers") == ["A", "C"], merged
        print("  ✅ A question that is logged twice ends up in a single row")


def test_mistake_store_merge_keeps_the_hand_written_content():
    """Test that the merge keeps the explanation of the newest row"""
    with tempfile.TemporaryDirectory() as tmp:
        store = MistakeStore(Path(tmp) / "mistakes.db")
        first = _record("What is demand?")
        first["explanation"] = ""
        first["wrong_answers"] = []
        store.upsert(first)
        # The question is logged again and the explanation is typed in
        second = _record("What is demand:")
        second["question_id"] = "q:other"
        second["explanation"] = "Because of the reason."
        second["wrong_answers"] = ["C"]
        store.upsert(second)

        assert store.merge_duplicates() == 1
        merged = store.load_by_question("what is demand")
        assert len(merged) == 1, merged
        assert merged[0].get("explanation") == "Because of the reason.", merged
        assert merged[0].get("wrong_answers") == ["C"], merged
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
        first["wrong_answers"] = ["A tariff"]
        first["correct_answer"] = "An import quota"
        first["explanation"] = "the demand falls when the price rises."
        store.upsert(first)
        # The same question, written with the punctuation and in upper case
        second = _record("What is demand:")
        second["question_id"] = "q:other"
        second["options"] = ["An import quota.", "A restraint.", "A tariff."]
        second["wrong_answers"] = ["A tariff."]
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
        assert record.get("wrong_answers") == ["A tariff."], record
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
        data = cast(dict[str, object], json.loads(target.read_text(encoding="utf-8")))
        records = cast(list[dict[str, object]], data["records"])
        assert len(records) == 1, data
        assert records[0]["question"] == "What is demand?", data
        # No half-written file is left behind
        assert not (root / "export.json.tmp").exists()
        print("  ✅ The log can be written as a JSON file again")
