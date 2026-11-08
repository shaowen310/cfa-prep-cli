"""
CFA Prep CLI - Quiz statistics module
Author: CodeBuddy AI Assistant
Purpose: Persist per-question quiz statistics at <data_root>/progress/quiz_stats.json,
         and provide a spaced-repetition style selection strategy that favours
         stale questions and repeatedly-wrong questions while reducing the frequency
         of questions the user has already learned.

         Every entry is a question, keyed by the hash of its identity.  The topic a
         question belongs to is deliberately not stored here: the curriculum and the
         mistake log own that mapping.
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict, cast

from .curriculum import subject_of, topic_of
from .utils import get_data_dir, load_json, save_json, today_iso


def local_today() -> date:
    """
    Return today's local date.

    Uses the timezone-aware local clock so the value is unambiguous and matches
    the user's own calendar day.
    """
    return datetime.now().astimezone().date()


# --- question identity ------------------------------------------------------
#
# Questions are keyed by the hash of their identity text (see :func:`question_id`
# in the mistake analyzer for the question scheme).  A curriculum question is
# identified by its curriculum label, so its id is derived there - this module
# only stores and schedules the ids it is given.


# --- scheduling constants ---------------------------------------------------

EASE_DEFAULT = 2.5   # SM-2 ease factor for a newly seen question
EASE_MIN = 1.3       # a badly-known question is never fully "forgiven"
EASE_MAX = 2.8       # a well-known question cannot become trivially easy
INTERVAL_LADDER = (1, 3, 7, 14)  # days after consecutive correct answers

# --- priority weights -------------------------------------------------------

UNSEEN_PRIORITY = 5.0      # never tested -> high attention
OVERDUE_CAP = 3.0          # max bonus for being long past due
WRONG_RATIO_WEIGHT = 4.0   # weight of the wrong-answer ratio
WRONG_COUNT_WEIGHT = 0.8   # weight per repeat mistake (capped at 5)
SKIP_WEIGHT = 1.5          # bonus for questions that were skipped (never answered)
MASTERY_DISCOUNT = 2.0     # max discount for a streak of correct answers

RESULT_CORRECT = "correct"
RESULT_WRONG = "wrong"
RESULT_SKIPPED = "skipped"


class QuestionStat(TypedDict):
    """Statistics kept for a single question."""
    question: str          # the question text (or the prompt that was answered)
    level: str             # "L1" | "L2" | "L3"
    source: str            # "mistake" | "topic" | "book"
    times_seen: int
    times_correct: int
    times_wrong: int
    times_skipped: int
    streak: int            # consecutive correct answers
    ease: float            # SM-2 ease factor
    interval_days: int     # current scheduling interval
    last_seen: str         # ISO date of the last attempt
    last_result: str       # "correct" | "wrong" | "skipped"


class SessionRecord(TypedDict):
    """Summary of one finished quiz session."""
    date: str
    level: str
    total: int
    correct: int
    wrong: int
    skipped: int


class QuizStatsData(TypedDict):
    """JSON shape of the per-question statistics file (quiz_stats.json)."""
    version: int
    updated: str
    questions: dict[str, QuestionStat]


class QuizSessionsData(TypedDict):
    """JSON shape of the session history file (quiz_sessions.json)."""
    version: int
    updated: str
    sessions: list[SessionRecord]


def _as_int(value: object, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    return float(value) if isinstance(value, (int, float)) else default


def _as_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def parse_date(value: str) -> date | None:
    """Parse an ISO date string, returning None when it is missing or invalid."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def describe(stat: QuestionStat, max_len: int = 60) -> str:
    """Return a short human-readable label for a statistics entry."""
    text = stat.get("question", "").strip()
    if text.startswith("["):
        # A curriculum question carries its label as the prompt that was answered.
        text = topic_of(text)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def next_due_of(stat: QuestionStat) -> date | None:
    """
    Return the date a question becomes due again.

    The due date is always derived from the last attempt plus the current
    scheduling interval, so it is never stored: there is a single source of
    truth and the two can never drift apart.

    Returns None when the question has never been attempted.
    """
    last_seen = parse_date(stat.get("last_seen", ""))
    if last_seen is None:
        return None
    return last_seen + timedelta(days=stat.get("interval_days", 0))


class QuizStats:
    """
    Quiz statistics tracker.

    Stores the outcome of every answered question, applies a spaced-repetition
    schedule to decide when it should come back, and scores questions by urgency
    so the quiz can focus on stale and repeatedly-wrong material.

    Questions are keyed by a hash of their identity (see :func:`question_id`
    and :func:`topic_id`), so the stored keys stay short and stable.

    The whole file is rewritten on every save, so writing after every single
    answer would re-read and re-serialize the entire file per question.  Pass
    ``autosave=False`` to keep the changes in memory and call :meth:`flush`
    once at the end instead.
    """

    def __init__(self, autosave: bool = True) -> None:
        self.stats_dir: Path = get_data_dir("progress")
        self.stats_file: Path = self.stats_dir / "quiz_stats.json"
        self.sessions_file: Path = self.stats_dir / "quiz_sessions.json"
        self.autosave: bool = autosave
        self._cache: QuizStatsData | None = None
        self._sessions_cache: QuizSessionsData | None = None
        self._dirty: bool = False
        self._sessions_dirty: bool = False

    # --- persistence -------------------------------------------------------

    def load(self, refresh: bool = False) -> QuizStatsData:
        """
        Load the per-question statistics, returning an empty structure if absent.

        The result is cached; pass ``refresh=True`` to force a re-read from disk.
        """
        if self._cache is not None and not refresh:
            return self._cache
        raw = load_json(self.stats_file)
        questions: dict[str, QuestionStat] = {}
        questions_raw = raw.get("questions", {})
        if isinstance(questions_raw, dict):
            for key, value in questions_raw.items():
                if isinstance(value, dict):
                    questions[key] = self._normalize_question(cast(dict[str, object], value))

        data = QuizStatsData(
            version=_as_int(raw.get("version"), 1),
            updated=_as_str(raw.get("updated"), today_iso()),
            questions=questions,
        )
        self._cache = data
        return data

    def load_sessions(self, refresh: bool = False) -> QuizSessionsData:
        """
        Load the session history, returning an empty structure if absent.

        The result is cached; pass ``refresh=True`` to force a re-read from disk.
        """
        if self._sessions_cache is not None and not refresh:
            return self._sessions_cache

        raw = load_json(self.sessions_file)

        sessions: list[SessionRecord] = []
        sessions_raw = raw.get("sessions", [])
        if isinstance(sessions_raw, list):
            for item in sessions_raw:
                if isinstance(item, dict):
                    d = cast(dict[str, object], item)
                    sessions.append(self._normalize_session(d))

        data = QuizSessionsData(
            version=_as_int(raw.get("version"), 1),
            updated=_as_str(raw.get("updated"), today_iso()),
            sessions=sessions,
        )
        self._sessions_cache = data
        return data

    def save(self, data: QuizStatsData) -> None:
        """Persist the per-question statistics file."""
        self._cache = data
        self._dirty = False
        save_json(self.stats_file, cast(dict[str, object], cast(object, data)))

    def save_sessions(self, data: QuizSessionsData) -> None:
        """Persist the session history file."""
        self._sessions_cache = data
        self._sessions_dirty = False
        save_json(self.sessions_file, cast(dict[str, object], cast(object, data)))

    def flush(self) -> None:
        """Write any pending changes to disk (no-op when nothing changed)."""
        if self._dirty and self._cache is not None:
            self.save(self._cache)
        if self._sessions_dirty and self._sessions_cache is not None:
            self.save_sessions(self._sessions_cache)

    @staticmethod
    def _normalize_question(raw: dict[str, object]) -> QuestionStat:
        return QuestionStat(
            question=_as_str(raw.get("question")),
            level=_as_str(raw.get("level")),
            source=_as_str(raw.get("source")),
            times_seen=_as_int(raw.get("times_seen")),
            times_correct=_as_int(raw.get("times_correct")),
            times_wrong=_as_int(raw.get("times_wrong")),
            times_skipped=_as_int(raw.get("times_skipped")),
            streak=_as_int(raw.get("streak")),
            ease=_as_float(raw.get("ease"), EASE_DEFAULT),
            interval_days=_as_int(raw.get("interval_days")),
            last_seen=_as_str(raw.get("last_seen")),
            last_result=_as_str(raw.get("last_result")),
        )

    @staticmethod
    def _normalize_session(raw: dict[str, object]) -> SessionRecord:
        return SessionRecord(
            date=_as_str(raw.get("date")),
            level=_as_str(raw.get("level")),
            total=_as_int(raw.get("total")),
            correct=_as_int(raw.get("correct")),
            wrong=_as_int(raw.get("wrong")),
            skipped=_as_int(raw.get("skipped")),
        )

    @staticmethod
    def _new_stat() -> QuestionStat:
        return QuestionStat(
            question="",
            level="",
            source="",
            times_seen=0,
            times_correct=0,
            times_wrong=0,
            times_skipped=0,
            streak=0,
            ease=EASE_DEFAULT,
            interval_days=0,
            last_seen="",
            last_result="",
        )

        # --- recording ---------------------------------------------------------

    @staticmethod
    def _next_interval(streak: int, current: int, ease: float) -> int:
        """Compute the next review interval (in days) for a correct answer."""
        if streak <= 1:
            return INTERVAL_LADDER[0]
        if streak <= len(INTERVAL_LADDER):
            return INTERVAL_LADDER[streak - 1]
        return max(1, round(max(current, 1) * ease))

    def record_question(
        self,
        key: str,
        result: str,
        question: str = "",
        level: str = "",
        source: str = "",
        today: date | None = None,
    ) -> None:
        """
        Record the outcome of one answered question and reschedule it.

        Parameters:
            key: question identity (see :func:`question_id` in the mistake analyzer)
            result: "correct" | "wrong" | "skipped"
            question: the question text (kept for reporting)
            level: exam level the question was asked at
            source: "mistake" | "topic" | "book"
            today: override for the current date (testing)
        """
        if not key:
            return
        day = today or local_today()
        data = self.load()
        questions = data["questions"]
        stat = questions.get(key) or self._new_stat()

        if question:
            stat["question"] = question
        if level:
            stat["level"] = level
        if source:
            stat["source"] = source

        stat["times_seen"] += 1
        stat["last_seen"] = day.isoformat()

        if result == RESULT_CORRECT:
            stat["times_correct"] += 1
            stat["streak"] += 1
            stat["ease"] = min(EASE_MAX, stat["ease"] + 0.1)
            stat["interval_days"] = self._next_interval(
                stat["streak"], stat["interval_days"], stat["ease"]
            )
            stat["last_result"] = RESULT_CORRECT
        elif result == RESULT_WRONG:
            stat["times_wrong"] += 1
            stat["streak"] = 0
            stat["ease"] = max(EASE_MIN, stat["ease"] - 0.2)
            stat["interval_days"] = 0
            stat["last_result"] = RESULT_WRONG
        else:
            stat["times_skipped"] += 1
            stat["streak"] = 0
            stat["ease"] = max(EASE_MIN, stat["ease"] - 0.1)
            stat["interval_days"] = 0
            stat["last_result"] = RESULT_SKIPPED

        questions[key] = stat
        data["questions"] = questions
        data["updated"] = today_iso()
        self._dirty = True
        if self.autosave:
            self.save(data)

    def record_session(
        self,
        level: str,
        total: int,
        correct: int,
        wrong: int,
        skipped: int,
    ) -> None:
        """Append a finished session to the history."""
        data = self.load_sessions()
        sessions = data["sessions"]
        sessions.append(
            SessionRecord(
                date=today_iso(),
                level=level,
                total=total,
                correct=correct,
                wrong=wrong,
                skipped=skipped,
            )
        )
        data["sessions"] = sessions[-200:]
        data["updated"] = today_iso()
        self._sessions_dirty = True
        if self.autosave:
            self.save_sessions(data)

    # --- scheduling / priority ---------------------------------------------

    @staticmethod
    def _priority_of(stat: QuestionStat | None, today: date) -> float:
        """
        Score how urgently a question should be asked.

        Higher = more urgent. Never-seen questions get a flat high score; known
        questions are scored from how overdue they are, how often they were
        answered wrongly, how stale they are, minus a discount for consecutive
        correct answers (which means the knowledge has been learnt).
        """
        if stat is None:
            return UNSEEN_PRIORITY

        priority = 0.0

        # 1. How long past due.  The interval already encodes how long a question
        #    may rest, so "overdue" also covers "not tested for a long time".
        due = next_due_of(stat)
        if due is None:
            overdue_days = 30
        else:
            overdue_days = (today - due).days
        priority += min(max(overdue_days, 0) / 7.0, OVERDUE_CAP)

        # 2. Repeatedly wrong answers.
        seen = max(stat["times_seen"], 1)
        wrong_ratio = stat["times_wrong"] / seen
        priority += WRONG_RATIO_WEIGHT * wrong_ratio
        priority += WRONG_COUNT_WEIGHT * min(stat["times_wrong"], 5)

        # 3. Skipped questions were never really tested, so they still need attention.
        priority += SKIP_WEIGHT * min(stat["times_skipped"], 2)

        # 4. Mastery discount: consecutive correct answers push it back.
        priority -= MASTERY_DISCOUNT * min(stat["streak"] / 3.0, 1.0)

        return priority

    def priority_of(self, key: str, today: date | None = None) -> float:
        """
        Return the urgency score of a single question.

        A question that was never seen gets a flat high score, so new material
        is still covered; a known question is scored from how overdue it is, how
        often it was answered wrongly and how stale it is, minus a discount for
        consecutive correct answers.
        """
        day = today or local_today()
        stat = self.load()["questions"].get(key)
        if stat is None:
            return UNSEEN_PRIORITY
        return self._priority_of(stat, day)

    def select_scored(self, scored: list[tuple[float, str]], count: int) -> list[str]:
        """
        Pick the items to quiz from a list of scored candidates.

        A fixed share (40%) is filled with the highest-priority items (stale /
        repeatedly wrong), and the rest is drawn at random from the remaining
        ones, weighted by priority so that moderately urgent items still show
        up regularly.

        Parameters:
            scored: the candidates as (priority, key) pairs
            count: number of items to select

        Returns:
            The selected keys, in quiz order.
        """
        if not scored or count <= 0:
            return []

        total = min(count, len(scored))
        num_priority = min(total, max(1, round(total * 0.4)))

        # Highest priority first, random tie-break so the order is not fixed.
        ordered = sorted(scored, key=lambda pair: (-pair[0], random.random()))
        selected: list[str] = [key for _, key in ordered[:num_priority]]

        # The rest is a weighted random draw (without replacement) so the quiz
        # keeps some variety while still favouring urgent items.
        remaining = total - len(selected)
        pool: list[tuple[float, str]] = ordered[num_priority:]
        while remaining > 0 and pool:
            weights = [max(0.1, score) for score, _ in pool]
            idx = random.choices(range(len(pool)), weights=weights, k=1)[0]
            selected.append(pool.pop(idx)[1])
            remaining -= 1

        random.shuffle(selected)
        return selected

    # --- reporting ---------------------------------------------------------

    def overall(self) -> dict[str, int]:
        """Aggregate totals across every recorded session."""
        data = self.load_sessions()
        sessions = data["sessions"]
        total = correct = wrong = skipped = 0
        for s in sessions:
            total += s["total"]
            correct += s["correct"]
            wrong += s["wrong"]
            skipped += s["skipped"]
        return {
            "sessions": len(sessions),
            "total": total,
            "correct": correct,
            "wrong": wrong,
            "skipped": skipped,
        }

    def by_subject(
        self, subject_by_id: dict[str, str] | None = None
    ) -> list[tuple[str, int, int, int]]:
        """
        Per-subject breakdown as (subject, seen, correct, wrong) tuples,
        sorted by accuracy ascending (weakest subject first).

        The subject is not stored with the question, so it is resolved in two
        ways: a curriculum question carries its label in the prompt text, and a
        logged mistake carries its subject in the mistake log - which the caller
        passes in as ``subject_by_id``.
        """
        data = self.load()
        mapping = subject_by_id or {}
        agg: dict[str, list[int]] = {}
        for key, stat in data["questions"].items():
            text = stat.get("question", "")
            subject = mapping.get(key) or (subject_of(text) if text.startswith("[") else "")
            row = agg.setdefault(subject or "(unclassified)", [0, 0, 0])
            row[0] += stat["times_seen"]
            row[1] += stat["times_correct"]
            row[2] += stat["times_wrong"]
        rows = [(s, v[0], v[1], v[2]) for s, v in agg.items()]
        rows.sort(key=lambda r: (r[1] - r[2], r[0]))
        return rows

    def weakest_questions(self, limit: int = 10) -> list[tuple[str, QuestionStat]]:
        """Questions answered wrongly most often, worst first."""
        data = self.load()
        rows = [
            (key, stat)
            for key, stat in data["questions"].items()
            if stat["times_wrong"] > 0
        ]
        rows.sort(key=lambda pair: (-pair[1]["times_wrong"], -pair[1]["times_seen"]))
        return rows[:limit]

    def due_questions(
        self, limit: int = 10, today: date | None = None
    ) -> list[tuple[str, QuestionStat, int]]:
        """Questions that are due (or overdue), most overdue first."""
        day = today or local_today()
        data = self.load()
        rows: list[tuple[str, QuestionStat, int]] = []
        for key, stat in data["questions"].items():
            due = next_due_of(stat)
            if due is None:
                continue
            overdue = (day - due).days
            if overdue >= 0:
                rows.append((key, stat, overdue))
        rows.sort(key=lambda row: -row[2])
        return rows[:limit]

    def mastered_questions(self) -> list[tuple[str, QuestionStat]]:
        """Questions answered correctly at least three times in a row."""
        data = self.load()
        return sorted(
            ((key, stat) for key, stat in data["questions"].items() if stat["streak"] >= 3),
            key=lambda pair: pair[0],
        )

    def reset(self) -> None:
        """Delete all stored statistics and session history."""
        empty_questions = QuizStatsData(version=1, updated=today_iso(), questions={})
        save_json(self.stats_file, cast(dict[str, object], cast(object, empty_questions)))
        empty_sessions = QuizSessionsData(version=1, updated=today_iso(), sessions=[])
        save_json(self.sessions_file, cast(dict[str, object], cast(object, empty_sessions)))
        self._cache = empty_questions
        self._sessions_cache = empty_sessions
        self._dirty = False
        self._sessions_dirty = False
