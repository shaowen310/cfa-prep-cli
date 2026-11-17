"""
CFA Prep CLI - Mistake store module
Author: CodeBuddy AI Assistant
Purpose: Keep the mistake log in an SQLite database (the standard library), so a
         mistake is written with one statement instead of rewriting the whole
         file, and every read is a query instead of a full parse.  The old JSON
         file is imported once and kept as a backup.
"""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TypedDict, cast

from .tables import Table

DB_NAME = "mistakes.db"
LEGACY_NAME = "mistakes.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS mistakes (
    question_id    TEXT PRIMARY KEY,
    date           TEXT NOT NULL DEFAULT '',
    last_date      TEXT NOT NULL DEFAULT '',
    attempts       INTEGER NOT NULL DEFAULT 1,
    level          TEXT NOT NULL DEFAULT '',
    subject        TEXT NOT NULL DEFAULT '',
    "module"       TEXT NOT NULL DEFAULT '',
    question       TEXT NOT NULL DEFAULT '',
    options        TEXT NOT NULL DEFAULT '[]',
    user_answer    TEXT NOT NULL DEFAULT '',
    correct_answer TEXT NOT NULL DEFAULT '',
    explanation    TEXT NOT NULL DEFAULT '',
    wrong_answers  TEXT NOT NULL DEFAULT '[]',
    table_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_mistakes_subject_module ON mistakes(subject, "module");
CREATE INDEX IF NOT EXISTS idx_mistakes_question ON mistakes(question);
CREATE INDEX IF NOT EXISTS idx_mistakes_date ON mistakes(date);
"""

UPSERT = """
INSERT INTO mistakes (
    question_id, date, last_date, attempts, level, subject, "module", question,
    options, user_answer, correct_answer, explanation, wrong_answers, table_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(question_id) DO UPDATE SET
    date           = excluded.date,
    last_date      = excluded.last_date,
    attempts       = excluded.attempts,
    level          = excluded.level,
    subject        = excluded.subject,
    "module"       = excluded."module",
    question       = excluded.question,
    options        = excluded.options,
    user_answer    = excluded.user_answer,
    correct_answer = excluded.correct_answer,
    explanation    = excluded.explanation,
    wrong_answers  = excluded.wrong_answers,
    table_json     = excluded.table_json
"""


class _MistakeRecordOptional(TypedDict, total=False):
    """The optional part of a mistake record."""
    table: Table | None
    attempts: int          # how often the mistake was logged
    last_date: str         # the date of the last attempt
    wrong_answers: list[str]  # the answers that were given wrong so far


class MistakeRecord(_MistakeRecordOptional):
    """One logged mistake: the question, the answers and what came with it."""
    date: str
    level: str
    subject: str
    module: str
    question: str
    question_id: str  # stable id of the question (hash of its text and options)
    options: list[str]  # [A text, B text, C text]
    user_answer: str     # the option text the user chose
    correct_answer: str  # the option text that is correct
    explanation: str


def _row_to_record(row: sqlite3.Row) -> MistakeRecord:
    """Build a mistake record from a database row."""
    record = MistakeRecord(
        date=row["date"],
        level=row["level"],
        subject=row["subject"],
        module=row["module"],
        question=row["question"],
        question_id=row["question_id"],
        options=cast(list[str], json.loads(row["options"] or "[]")),
        user_answer=row["user_answer"],
        correct_answer=row["correct_answer"],
        explanation=row["explanation"],
        attempts=row["attempts"],
    )
    if row["last_date"]:
        record["last_date"] = row["last_date"]
    wrong_answers = cast(list[str], json.loads(row["wrong_answers"] or "[]"))
    if wrong_answers:
        record["wrong_answers"] = wrong_answers
    if row["table_json"]:
        record["table"] = cast(Table, json.loads(row["table_json"]))
    return record


def _record_values(record: MistakeRecord) -> tuple[object, ...]:
    """Return the values of a record, in the order of the columns."""
    table = record.get("table")
    return (
        record.get("question_id", ""),
        record.get("date", ""),
        record.get("last_date", ""),
        record.get("attempts", 1),
        record.get("level", ""),
        record.get("subject", ""),
        record.get("module", ""),
        record.get("question", ""),
        json.dumps(record.get("options") or [], ensure_ascii=False),
        record.get("user_answer", ""),
        record.get("correct_answer", ""),
        record.get("explanation", ""),
        json.dumps(record.get("wrong_answers") or [], ensure_ascii=False),
        json.dumps(table, ensure_ascii=False) if table else None,
    )


def read_json_records(path: Path) -> list[MistakeRecord]:
    """Read the records of the old JSON log."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records = data.get("records", [])
    if not isinstance(records, list):
        return []
    return cast(list[MistakeRecord], records)


class MistakeStore:
    """
    The mistake log, kept in an SQLite database.

    The database is the live store: a mistake is written with one statement,
    the rows are found by index, and the log is never rewritten as a whole.
    The old JSON file is imported once and then kept as a backup.
    """

    db_path: Path
    legacy_path: Path | None

    def __init__(self, db_path: Path, legacy_path: Path | None = None) -> None:
        self.db_path = db_path
        self.legacy_path = legacy_path

    @contextmanager
    def _session(self) -> Generator[sqlite3.Connection, None, None]:
        """A connection that is committed at the end and closed afterwards."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            _ = connection.executescript(SCHEMA)
            with connection:
                yield connection
        finally:
            connection.close()

    # --- reading -----------------------------------------------------------

    def load_all(self) -> list[MistakeRecord]:
        """Return every record, in the order it was logged."""
        with self._session() as connection:
            rows = connection.execute("SELECT * FROM mistakes ORDER BY rowid").fetchall()
        return [_row_to_record(row) for row in rows]

    def load_recent(self, limit: int = 10) -> list[MistakeRecord]:
        """Return the newest records, the newest first."""
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM mistakes ORDER BY date DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def load_by_subject_module(
        self, subject: str, module: str
    ) -> list[MistakeRecord]:
        """Return the records of one module, in the order they were logged."""
        with self._session() as connection:
            rows = connection.execute(
                'SELECT * FROM mistakes WHERE subject = ? AND "module" = ? ORDER BY rowid',
                (subject, module),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def load_by_question(self, question: str) -> list[MistakeRecord]:
        """Return the records whose question text matches, ignoring the case."""
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM mistakes WHERE question = ? COLLATE NOCASE ORDER BY rowid",
                (question,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def get(self, question_id: str) -> MistakeRecord | None:
        """Return the record of that question, when it is logged."""
        if not question_id:
            return None
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM mistakes WHERE question_id = ?", (question_id,)
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    def grouped_counts(self) -> list[tuple[str, str, int, int]]:
        """
        Return (subject, module, questions, attempts) for every group.

        The counts come from the database, so the log does not have to be
        loaded to know how much of it there is.
        """
        with self._session() as connection:
            rows = connection.execute(
                "SELECT subject, \"module\" AS module, COUNT(*) AS questions,"
                " SUM(attempts) AS attempts FROM mistakes"
                " GROUP BY subject, \"module\" ORDER BY subject, \"module\""
            ).fetchall()
        return [
            (row["subject"], row["module"], row["questions"], row["attempts"])
            for row in rows
        ]

    def count(self) -> int:
        """Return the number of logged questions."""
        with self._session() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM mistakes").fetchone()
        return int(row["total"]) if row is not None else 0

    # --- writing -----------------------------------------------------------

    def upsert(self, record: MistakeRecord) -> None:
        """Write the record, replacing the row that has the same question id."""
        with self._session() as connection:
            _ = connection.execute(UPSERT, _record_values(record))

    def replace_all(self, records: list[MistakeRecord]) -> None:
        """Write the log from scratch: the old rows are dropped first."""
        with self._session() as connection:
            _ = connection.execute("DELETE FROM mistakes")
            _ = connection.executemany(
                UPSERT, [_record_values(record) for record in records]
            )

    def delete(self, question_id: str) -> bool:
        """Remove a question from the log."""
        with self._session() as connection:
            cursor = connection.execute(
                "DELETE FROM mistakes WHERE question_id = ?", (question_id,)
            )
            return cursor.rowcount > 0

    # --- moving between the formats ---------------------------------------

    def import_legacy(self) -> int:
        """
        Import the old JSON log into the database, once.

        The import only happens while the database is still empty, so a JSON
        file that shows up later is never mixed into a log that is in use.  The
        file is kept as a backup under a new name, so nothing is lost.
        """
        if self.legacy_path is None or not self.legacy_path.exists():
            return 0
        if self.count() > 0:
            return 0
        records = read_json_records(self.legacy_path)
        with self._session() as connection:
            for record in records:
                _ = connection.execute(UPSERT, _record_values(record))
        backup = self.legacy_path.with_name(self.legacy_path.name + ".imported")
        _ = self.legacy_path.replace(backup)
        return len(records)

    def export_json(self, path: Path) -> None:
        """Write the log as a JSON file, the format that can be read by hand."""
        path.parent.mkdir(parents=True, exist_ok=True)
        records = self.load_all()
        temp = path.with_name(path.name + ".tmp")
        try:
            with open(temp, "w", encoding="utf-8") as f:
                json.dump({"records": list(records)}, f, ensure_ascii=False, indent=2)
                f.flush()
            _ = temp.replace(path)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
