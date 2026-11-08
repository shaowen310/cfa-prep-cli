"""
CFA Prep CLI - Quiz statistics module
Author: CodeBuddy AI Assistant
Purpose: Persist per-topic quiz statistics at <data_root>/progress/quiz_stats.json,
         and provide a spaced-repetition style selection strategy that favours
         stale topics and repeatedly-wrong topics while reducing the frequency
         of topics the user has already learned.
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict, cast

from .utils import get_data_dir, load_json, save_json, today_iso


def local_today() -> date:
    """
    Return today's local date.

    Uses the timezone-aware local clock so the value is unambiguous and matches
    the user's own calendar day.
    """
    return datetime.now().astimezone().date()

# --- scheduling constants ---------------------------------------------------

EASE_DEFAULT = 2.5   # SM-2 ease factor for a newly seen topic
EASE_MIN = 1.3       # a badly-known topic is never fully "forgiven"
EASE_MAX = 2.8       # a well-known topic cannot become trivially easy
INTERVAL_LADDER = (1, 3, 7, 14)  # days after consecutive correct answers

# --- priority weights -------------------------------------------------------

UNSEEN_PRIORITY = 5.0      # never tested -> high attention
OVERDUE_CAP = 3.0          # max bonus for being long past due
WRONG_RATIO_WEIGHT = 4.0   # weight of the wrong-answer ratio
WRONG_COUNT_WEIGHT = 0.8   # weight per repeat mistake (capped at 5)
SKIP_WEIGHT = 1.5          # bonus for topics that were skipped (never answered)
MASTERY_DISCOUNT = 2.0     # max discount for a streak of correct answers
BOOST_AMOUNT = 1.5         # extra priority for topics in the mistake/fuzzy lists

RESULT_CORRECT = "correct"
RESULT_WRONG = "wrong"
RESULT_SKIPPED = "skipped"


class TopicStat(TypedDict):
    """Statistics kept for a single topic."""
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
    """JSON shape of the statistics file."""
    version: int
    updated: str
    sessions: list[SessionRecord]
    topics: dict[str, TopicStat]


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


def subject_of(label: str) -> str:
    """Extract the subject from a "[Subject > Module] Topic" label."""
    bracket = label.find("]")
    if bracket == -1:
        return ""
    inner = label[1:bracket]
    if ">" in inner:
        return inner.split(">", 1)[0].strip()
    return inner.strip()


def topic_of(label: str) -> str:
    """Extract the plain topic text from a "[Subject > Module] Topic" label."""
    idx = label.rfind("] ")
    return label[idx + 2:] if idx != -1 else label


def next_due_of(stat: TopicStat) -> date | None:
    """
    Return the date a topic becomes due again.

    The due date is always derived from the last attempt plus the current
    scheduling interval, so it is never stored: there is a single source of
    truth and the two can never drift apart.

    Returns None when the topic has never been attempted.
    """
    last_seen = parse_date(stat.get("last_seen", ""))
    if last_seen is None:
        return None
    return last_seen + timedelta(days=stat.get("interval_days", 0))


class QuizStats:
    """
    Quiz statistics tracker.

    Stores per-topic outcomes, applies a spaced-repetition schedule to decide
    when a topic should come back, and scores topics by urgency so the quiz can
    focus on stale and repeatedly-wrong material.

    The whole file is rewritten on every save, so writing after every single
    answer would re-read and re-serialize the entire file per question.  Pass
    ``autosave=False`` to keep the changes in memory and call :meth:`flush`
    once at the end instead.
    """

    def __init__(self, autosave: bool = True) -> None:
        self.stats_dir: Path = get_data_dir("progress")
        self.stats_file: Path = self.stats_dir / "quiz_stats.json"
        self.autosave: bool = autosave
        self._cache: QuizStatsData | None = None
        self._dirty: bool = False

    # --- persistence -------------------------------------------------------

    def load(self, refresh: bool = False) -> QuizStatsData:
        """
        Load the statistics file, returning an empty structure if absent.

        The result is cached; pass ``refresh=True`` to force a re-read from disk.
        """
        if self._cache is not None and not refresh:
            return self._cache
        raw = load_json(self.stats_file)
        topics: dict[str, TopicStat] = {}
        topics_raw = raw.get("topics", {})
        if isinstance(topics_raw, dict):
            for key, value in topics_raw.items():
                if isinstance(value, dict):
                    topics[key] = self._normalize_topic(cast(dict[str, object], value))

        sessions: list[SessionRecord] = []
        sessions_raw = raw.get("sessions", [])
        if isinstance(sessions_raw, list):
            for item in sessions_raw:
                if isinstance(item, dict):
                    d = cast(dict[str, object], item)
                    sessions.append(self._normalize_session(d))

        data = QuizStatsData(
            version=_as_int(raw.get("version"), 1),
            updated=_as_str(raw.get("updated"), today_iso()),
            sessions=sessions,
            topics=topics,
        )
        self._cache = data
        return data

    def save(self, data: QuizStatsData) -> None:
        """Persist the statistics file."""
        self._cache = data
        self._dirty = False
        save_json(self.stats_file, cast(dict[str, object], cast(object, data)))

    def flush(self) -> None:
        """Write any pending changes to disk (no-op when nothing changed)."""
        if self._dirty and self._cache is not None:
            self.save(self._cache)

    @staticmethod
    def _normalize_topic(raw: dict[str, object]) -> TopicStat:
        return TopicStat(
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
    def _new_stat() -> TopicStat:
        return TopicStat(
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

    def record(self, topic: str, result: str, today: date | None = None) -> None:
        """
        Record the outcome of one answered topic and reschedule it.

        Parameters:
            topic: curriculum topic label (or plain key point)
            result: "correct" | "wrong" | "skipped"
            today: override for the current date (testing)
        """
        if not topic:
            return
        day = today or local_today()
        data = self.load()
        topics = data["topics"]
        stat = topics.get(topic) or self._new_stat()

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

        topics[topic] = stat
        data["topics"] = topics
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
        data = self.load()
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
        self._dirty = True
        if self.autosave:
            self.save(data)

    # --- scheduling / priority ---------------------------------------------

    @staticmethod
    def _priority_of(stat: TopicStat | None, today: date) -> float:
        """
        Score how urgently a topic should be asked.

        Higher = more urgent. Never-seen topics get a flat high score; known
        topics are scored from how overdue they are, how often they were answered
        wrongly, how stale they are, minus a discount for consecutive correct
        answers (which means the knowledge has been learnt).
        """
        if stat is None:
            return UNSEEN_PRIORITY

        priority = 0.0

        # 1. How long past due.  The interval already encodes how long a topic may
        #    rest, so "overdue" also covers "not tested for a long time".
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

        # 3. Skipped topics were never really tested, so they still need attention.
        priority += SKIP_WEIGHT * min(stat["times_skipped"], 2)

        # 4. Mastery discount: consecutive correct answers push it back.
        priority -= MASTERY_DISCOUNT * min(stat["streak"] / 3.0, 1.0)

        return priority

    def priority(self, topic: str, today: date | None = None) -> float:
        """Public accessor for the urgency score of a single topic."""
        data = self.load()
        return self._priority_of(data["topics"].get(topic), today or local_today())

    def select_topics(
        self,
        candidates: list[str],
        count: int,
        boosted: set[str] | None = None,
        today: date | None = None,
    ) -> list[str]:
        """
        Select the topics to quiz.

        A fixed share (40%) of the quiz is filled with the highest-priority
        topics (stale / repeatedly wrong), and the rest is drawn at random from
        the remaining topics, weighted by priority so that moderately urgent
        topics still show up regularly.

        Parameters:
            candidates: all topics available for the level
            count: number of topics to select
            boosted: extra-priority topics (e.g. logged mistakes, fuzzy points)
            today: override for the current date (testing)

        Returns:
            The selected topics, in quiz order.
        """
        if not candidates or count <= 0:
            return []

        day = today or local_today()
        data = self.load()
        topics = data["topics"]
        boost_set = boosted or set()

        scored: list[tuple[float, str]] = []
        for topic in candidates:
            score = self._priority_of(topics.get(topic), day)
            if topic in boost_set:
                score += BOOST_AMOUNT
            scored.append((score, topic))

        total = min(count, len(candidates))
        num_priority = min(total, max(1, round(total * 0.4)))

        # Highest priority first, random tie-break so the order is not fixed.
        ordered = sorted(scored, key=lambda pair: (-pair[0], random.random()))
        selected: list[str] = [topic for _, topic in ordered[:num_priority]]

        # The rest is a weighted random draw (without replacement) so the quiz
        # keeps some variety while still favouring urgent topics.
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
        data = self.load()
        total = correct = wrong = skipped = 0
        for s in data["sessions"]:
            total += s["total"]
            correct += s["correct"]
            wrong += s["wrong"]
            skipped += s["skipped"]
        return {
            "sessions": len(data["sessions"]),
            "total": total,
            "correct": correct,
            "wrong": wrong,
            "skipped": skipped,
        }

    def by_subject(self) -> list[tuple[str, int, int, int]]:
        """
        Per-subject breakdown as (subject, seen, correct, wrong) tuples,
        sorted by accuracy ascending (weakest subject first).
        """
        data = self.load()
        agg: dict[str, list[int]] = {}
        for topic, stat in data["topics"].items():
            subject = subject_of(topic) or "(unclassified)"
            row = agg.setdefault(subject, [0, 0, 0])
            row[0] += stat["times_seen"]
            row[1] += stat["times_correct"]
            row[2] += stat["times_wrong"]
        rows = [(s, v[0], v[1], v[2]) for s, v in agg.items()]
        rows.sort(key=lambda r: (r[1] - r[2], r[0]))
        return rows

    def weakest_topics(self, limit: int = 10) -> list[tuple[str, TopicStat]]:
        """Topics answered wrongly most often, worst first."""
        data = self.load()
        rows = [(t, s) for t, s in data["topics"].items() if s["times_wrong"] > 0]
        rows.sort(key=lambda pair: (-pair[1]["times_wrong"], -pair[1]["times_seen"]))
        return rows[:limit]

    def due_topics(self, limit: int = 10, today: date | None = None) -> list[tuple[str, int]]:
        """Topics that are due (or overdue), most overdue first."""
        day = today or local_today()
        data = self.load()
        rows: list[tuple[str, int]] = []
        for topic, stat in data["topics"].items():
            due = next_due_of(stat)
            if due is None:
                continue
            overdue = (day - due).days
            if overdue >= 0:
                rows.append((topic, overdue))
        rows.sort(key=lambda pair: -pair[1])
        return rows[:limit]

    def mastered_topics(self) -> list[str]:
        """Topics answered correctly at least three times in a row."""
        data = self.load()
        return sorted(t for t, s in data["topics"].items() if s["streak"] >= 3)

    def reset(self) -> None:
        """Delete all stored statistics."""
        empty = QuizStatsData(version=1, updated=today_iso(), sessions=[], topics={})
        save_json(self.stats_file, cast(dict[str, object], cast(object, empty)))
