"""
CFA Prep CLI - Mistake store module
Author: CodeBuddy AI Assistant
Purpose: Keep the mistake log in an SQLite database (the standard library), so a
         mistake is written with one statement instead of rewriting the whole
         file, and every read is a query instead of a full parse.
"""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TypedDict, cast

from .tables import Table
from .utils import (
    capitalize_first,
    normalize_text,
    prefer_text,
    stem_key,
)

DB_NAME = "mistakes.db"
MAX_WRONG_ANSWERS = 5  # how many wrong answers of a question are kept


def reconcile_options(old: list[str], new: list[str]) -> tuple[list[str], dict[str, str]]:
    """
    Return the options of a question and the map of the texts that changed.

    The options are matched on their key (the case and the spacing do not
    count), so a different order is not a problem.  The variant that ends with
    punctuation wins over the one that does not, and the map says which text
    became which, so the answers can be written the same way.
    """
    old_by_key = {normalize_text(option): option for option in old}
    options: list[str] = []
    mapping: dict[str, str] = {}
    for option in new:
        key = normalize_text(option)
        previous = old_by_key.get(key, "")
        chosen = prefer_text(previous, option)
        options.append(chosen)
        if previous:
            mapping[previous] = chosen
        mapping[option] = chosen
    return options, mapping

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
    stem_key       TEXT NOT NULL DEFAULT '',
    options        TEXT NOT NULL DEFAULT '[]',
    user_answer    TEXT NOT NULL DEFAULT '',
    correct_answer TEXT NOT NULL DEFAULT '',
    explanation    TEXT NOT NULL DEFAULT '',
    wrong_answers  TEXT NOT NULL DEFAULT '[]',
    table_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_mistakes_subject_module ON mistakes(subject, "module");
CREATE INDEX IF NOT EXISTS idx_mistakes_date ON mistakes(date);
CREATE INDEX IF NOT EXISTS idx_mistakes_stem_key ON mistakes(stem_key);
"""

UPSERT = """
INSERT INTO mistakes (
    question_id, date, last_date, attempts, level, subject, "module", question,
    stem_key, options, user_answer, correct_answer, explanation, wrong_answers,
    table_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(question_id) DO UPDATE SET
    date           = excluded.date,
    last_date      = excluded.last_date,
    attempts       = excluded.attempts,
    level          = excluded.level,
    subject        = excluded.subject,
    "module"       = excluded."module",
    question       = excluded.question,
    stem_key       = excluded.stem_key,
    options        = excluded.options,
    user_answer    = excluded.user_answer,
    correct_answer = excluded.correct_answer,
    explanation    = excluded.explanation,
    wrong_answers  = excluded.wrong_answers,
    table_json     = excluded.table_json
"""


def _rows(cursor: sqlite3.Cursor) -> list[sqlite3.Row]:
    """The rows of a query, with the type of the row known."""
    return cast(list[sqlite3.Row], cursor.fetchall())


def _row(cursor: sqlite3.Cursor) -> sqlite3.Row | None:
    """The row of a query, with the type of the row known."""
    return cast(sqlite3.Row | None, cursor.fetchone())


def _text(row: sqlite3.Row, column: str) -> str:
    """The text of a column of a row of the database.

    A column that holds nothing is an empty text.
    """
    value = cast(object, row[column])
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def _number(row: sqlite3.Row, column: str) -> int:
    """The number of a column of a row of the database."""
    value = cast(object, row[column])
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _texts(row: sqlite3.Row, column: str) -> list[str]:
    """The list of texts that is stored in a column of a row."""
    raw = _text(row, column)
    if not raw:
        return []
    values = cast(list[object], json.loads(raw))
    return [str(value) for value in values]


def _table_of(row: sqlite3.Row, column: str) -> Table | None:
    """The table that is stored in a column of a row."""
    raw = _text(row, column)
    if not raw:
        return None
    return cast(Table, json.loads(raw))


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create the table and its indexes."""
    _ = connection.executescript(SCHEMA)


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
        date=_text(row, "date"),
        level=_text(row, "level"),
        subject=_text(row, "subject"),
        module=_text(row, "module"),
        question=_text(row, "question"),
        question_id=_text(row, "question_id"),
        options=_texts(row, "options"),
        user_answer=_text(row, "user_answer"),
        correct_answer=_text(row, "correct_answer"),
        explanation=_text(row, "explanation"),
        attempts=_number(row, "attempts"),
    )
    last_date = _text(row, "last_date")
    if last_date:
        record["last_date"] = last_date
    wrong_answers = _texts(row, "wrong_answers")
    if wrong_answers:
        record["wrong_answers"] = wrong_answers
    table = _table_of(row, "table_json")
    if table:
        record["table"] = table
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
        # The key is always derived from the question, never stored by hand
        stem_key(record.get("question", "")),
        json.dumps(record.get("options") or [], ensure_ascii=False),
        record.get("user_answer", ""),
        record.get("correct_answer", ""),
        record.get("explanation", ""),
        json.dumps(record.get("wrong_answers") or [], ensure_ascii=False),
        json.dumps(table, ensure_ascii=False) if table else None,
    )


class MistakeStore:
    """
    The mistake log, kept in an SQLite database.

    The database is the live store: a mistake is written with one statement,
    the rows are found by index, and the log is never rewritten as a whole.
    """

    db_path: Path

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @contextmanager
    def _session(self) -> Generator[sqlite3.Connection, None, None]:
        """A connection that is committed at the end and closed afterwards."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                _ensure_schema(connection)
                yield connection
        finally:
            connection.close()

    # --- reading -----------------------------------------------------------

    def load_all(self) -> list[MistakeRecord]:
        """Return every record, in the order it was logged."""
        with self._session() as connection:
            rows = _rows(connection.execute("SELECT * FROM mistakes ORDER BY rowid"))
        return [_row_to_record(row) for row in rows]

    def load_recent(self, limit: int = 10) -> list[MistakeRecord]:
        """Return the newest records, the newest first."""
        with self._session() as connection:
            rows = _rows(
                connection.execute(
                    "SELECT * FROM mistakes ORDER BY date DESC, rowid DESC LIMIT ?",
                    (limit,),
                )
            )
        return [_row_to_record(row) for row in rows]

    def load_by_subject_module(
        self, subject: str, module: str
    ) -> list[MistakeRecord]:
        """Return the records of one module, in the order they were logged."""
        with self._session() as connection:
            rows = _rows(
                connection.execute(
                    'SELECT * FROM mistakes WHERE subject = ? AND "module" = ? ORDER BY rowid',
                    (subject, module),
                )
            )
        return [_row_to_record(row) for row in rows]

    def load_by_question(self, question: str) -> list[MistakeRecord]:
        """
        Return the records of that question.

        The question is matched on its key: the case, the spacing and the
        punctuation that closes the sentence do not count, so a question that is
        typed again as "... most likely:" is recognised as the "... most likely"
        that is already logged.
        """
        key = stem_key(question)
        if not key:
            return []
        with self._session() as connection:
            rows = _rows(
                connection.execute(
                    "SELECT * FROM mistakes WHERE stem_key = ? ORDER BY rowid", (key,)
                )
            )
        return [_row_to_record(row) for row in rows]

    def get(self, question_id: str) -> MistakeRecord | None:
        """Return the record of that question, when it is logged."""
        if not question_id:
            return None
        with self._session() as connection:
            row = _row(
                connection.execute(
                    "SELECT * FROM mistakes WHERE question_id = ?", (question_id,)
                )
            )
        return _row_to_record(row) if row is not None else None

    def grouped_counts(self) -> list[tuple[str, str, int, int]]:
        """
        Return (subject, module, questions, attempts) for every group.

        The counts come from the database, so the log does not have to be
        loaded to know how much of it there is.
        """
        with self._session() as connection:
            rows = _rows(
                connection.execute(
                    'SELECT subject, "module" AS module, COUNT(*) AS questions,'
                    + " SUM(attempts) AS attempts FROM mistakes"
                    + ' GROUP BY subject, "module" ORDER BY subject, "module"'
                )
            )
        return [
            (
                _text(row, "subject"),
                _text(row, "module"),
                _number(row, "questions"),
                _number(row, "attempts"),
            )
            for row in rows
        ]

    def count(self) -> int:
        """Return the number of logged questions."""
        with self._session() as connection:
            row = _row(
                connection.execute("SELECT COUNT(*) AS total FROM mistakes")
            )
        return _number(row, "total") if row is not None else 0

    def latest(self) -> MistakeRecord | None:
        """Return the question that was logged last, when there is one."""
        with self._session() as connection:
            row = _row(
                connection.execute(
                    "SELECT * FROM mistakes"
                    + " ORDER BY COALESCE(NULLIF(last_date, ''), date) DESC, rowid DESC"
                    + " LIMIT 1"
                )
            )
        return _row_to_record(row) if row is not None else None

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

    def duplicate_groups(self) -> list[list[MistakeRecord]]:
        """
        Return the groups of rows that hold the same question.

        The rows of a group share the key of the question, so they are the same
        question that was logged more than once — usually under a slightly
        different text.  The oldest row of a group comes first.
        """
        with self._session() as connection:
            rows = _rows(
                connection.execute(
                    "SELECT * FROM mistakes WHERE stem_key != '' ORDER BY rowid"
                )
            )
        groups: dict[str, list[MistakeRecord]] = {}
        for row in rows:
            key = _text(row, "stem_key")
            groups.setdefault(key, []).append(_row_to_record(row))
        return [group for group in groups.values() if len(group) > 1]

    def merge_duplicates(self) -> int:
        """
        Merge the rows that hold the same question into a single row.

        The oldest row is kept — it holds the id and the first date — and the
        attempts and the wrong answers of the other ones are folded into it.

        The texts are written the most careful way: a text that ends with
        punctuation wins over the same text without it, and a sentence starts
        with a capital letter.  Returns the number of rows that were removed.
        """
        removed = 0
        for group in self.duplicate_groups():
            keep = group[0]
            newest = group[-1]

            # The question: the variant that is written the most carefully
            question = keep.get("question", "")
            for other in group[1:]:
                question = prefer_text(question, other.get("question", ""))

            # The options: matched on their key, the punctuation decides
            options = list(keep.get("options") or [])
            mapping: dict[str, str] = {}
            for other in group[1:]:
                other_options = list(other.get("options") or [])
                if not other_options:
                    continue
                options, extra = reconcile_options(options, other_options)
                composed = dict(mapping)
                for source, target in extra.items():
                    composed[source] = mapping.get(target, target)
                mapping = composed

            # The answers are written the way the options they belong to are
            user_answer = prefer_text(
                keep.get("user_answer", ""), newest.get("user_answer", "")
            )
            correct_answer = prefer_text(
                keep.get("correct_answer", ""), newest.get("correct_answer", "")
            )
            user_answer = mapping.get(user_answer, user_answer)
            correct_answer = mapping.get(correct_answer, correct_answer)

            explanation = prefer_text(
                keep.get("explanation", ""), newest.get("explanation", "")
            )

            merged = MistakeRecord(
                date=keep.get("date", ""),
                level=keep.get("level", ""),
                subject=keep.get("subject", ""),
                module=keep.get("module", ""),
                question=capitalize_first(question),
                question_id=keep["question_id"],
                options=options,
                user_answer=user_answer,
                correct_answer=correct_answer,
                explanation=capitalize_first(explanation),
            )
            table = newest.get("table") or keep.get("table")
            if table:
                merged["table"] = table

            # The history of the attempts is folded into the row that is kept
            attempts = 0
            wrong: list[str] = []
            for record in group:
                attempts += int(record.get("attempts", 1))
                for answer in record.get("wrong_answers") or []:
                    written = mapping.get(answer, answer)
                    if written not in wrong:
                        wrong.append(written)
            merged["attempts"] = attempts
            merged["wrong_answers"] = wrong[-MAX_WRONG_ANSWERS:]
            merged["last_date"] = max(
                str(record.get("last_date") or record.get("date", ""))
                for record in group
            )

            self.upsert(merged)
            for other in group[1:]:
                _ = self.delete(other["question_id"])
                removed += 1
        return removed

    # --- exporting ---------------------------------------------------------
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
