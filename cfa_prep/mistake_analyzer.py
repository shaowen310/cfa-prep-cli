# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Mistake analyzer module
Author: CodeBuddy AI Assistant
Purpose: Log and analyze mistakes, stored as JSON at <data_root>/mistakes/mistakes.json.
         Supports MCQ (L1) and free-form (L2/L3) mistake logging.
"""

from pathlib import Path
from typing import TypedDict, cast

from .utils import (
    get_data_dir,
    hash_text,
    normalize_text,
    print_section,
    today_str,
    load_json,
    save_json,
)
from .curriculum import Curriculum

QUESTION_PREFIX = "q:"   # identity derived from the question text


def question_id(stem: str, options: list[str] | None = None) -> str:
    """
    Return the stable id of a question.

    The id is a hash of the question text plus its options.  Hashing keeps the
    stored key short (18 characters instead of the whole question) and makes it
    immune to formatting changes, while the options are part of the identity
    because two different questions can share the same stem.

    The options are hashed in sorted order, so the identity does not depend on
    the order the options happen to be displayed in.

    The correct answer is deliberately NOT part of the id, so re-logging a
    question with a corrected answer keeps its history attached.
    """
    normalized = sorted(normalize_text(option) for option in (options or []))
    return QUESTION_PREFIX + hash_text(stem, "\n".join(normalized))


def _session_label(subject: str, module_name: str) -> str:
    """
    Return the "Subject > Module" label of a mistake-logging session.

    Either part may be missing, so the label falls back to whichever one is
    known and is empty when neither is.
    """
    if subject and module_name:
        return f"{subject} > {module_name}"
    return subject or module_name


class MistakeRecord(TypedDict):
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


class MistakeAnalyzer:
    """
    Mistake analyzer.
    Manages the entry, categorization, storage, and retrieval of mistakes.
    All records stored in a single mistakes.json file.
    """

    def __init__(self):
        self.mistakes_dir: Path = get_data_dir("mistakes")
        self.data_file: Path = self.mistakes_dir / "mistakes.json"

    def _load(self) -> list[MistakeRecord]:
        """Load all mistake records."""
        data = load_json(self.data_file)
        records = data.get("records", [])
        if not isinstance(records, list):
            return []
        records_typed = cast(list[MistakeRecord], records)
        return list(records_typed)

    def _save(self, records: list[MistakeRecord]) -> None:
        """Save all mistake records."""
        save_json(self.data_file, {"records": list(records)})

    def _find_duplicates(self, question: str) -> list[MistakeRecord]:
        """
        Find previously logged mistakes whose question text matches the given one
        (case-insensitive). Used to warn the user before re-adding a question,
        since the same title may have different options.
        """
        q = question.strip().lower()
        if not q:
            return []
        return [r for r in self._load() if r.get("question", "").strip().lower() == q]

    def _confirm_duplicate(self, question: str) -> bool:
        """
        If the question was already logged, show the full previous record(s) and
        ask whether to continue adding anyway. Returns True to proceed, False to skip.
        """
        dups = self._find_duplicates(question)
        if not dups:
            return True
        print("\n  ⚠️  This question was already logged before:")
        for i, r in enumerate(dups, 1):
            print(f"  {'─' * 46}")
            print(f"  [{i}] {r.get('question', '')}")
            options = r.get("options") or []
            if options:
                for letter, opt in zip("ABC", options):
                    print(f"      {letter}. {opt}")
            if r.get("correct_answer"):
                print(f"      ✅ Correct: {r['correct_answer']}")
            if r.get("date"):
                print(f"      🗓 Date: {r['date']}")
        choice = self._prompt("\nAdd it again anyway? [y/N]: ").strip().lower()
        return choice in ("y", "yes")

    def add_mistake(
        self,
        subject: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        explanation: str,
        module_name: str = "",
        level: str = "L1",
        options: list[str] | None = None,
        existing_question_id: str = "",
    ) -> str:
        """
        Add a mistake record to mistakes.json.

        Parameters:
            subject: subject name (e.g., Economics)
            question: question text (without options)
            user_answer: the user's incorrect answer
            correct_answer: the correct answer
            explanation: the explanation of the correct answer
            module_name: module within the subject (required)
            level: exam level (L1/L2/L3)
            options: list of option texts [A, B, C] for MCQ (optional)
            existing_question_id: id of an already known question (e.g. when a
                record is re-logged); when empty it is derived from the question
                text and options

        Returns:
            the path of the mistakes file
        """
        # The subject and module are curriculum values, so they are the reliable
        # link between a mistake and the material it belongs to.  A mistake
        # without a module cannot be attributed, so it is rejected.
        if not module_name.strip():
            raise ValueError("A mistake needs a module to belong to.")
        records = self._load()
        # The question id is created once, here, and stored with the record.
        # Everything downstream reads it from this file, so the id of a
        # question is never derived twice from different texts.
        qid = existing_question_id.strip()
        if not qid and question.strip():
            qid = question_id(question, options or [])
        records.append(MistakeRecord(
            date=today_str(),
            level=level,
            subject=subject,
            module=module_name,
            question=question,
            question_id=qid,
            options=options or [],
            user_answer=user_answer,
            correct_answer=correct_answer,
            explanation=explanation,
        ))
        self._save(records)
        return str(self.data_file)

    @staticmethod
    def _prompt(prompt: str = "") -> str:
        """
        Read a line of input.  On Ctrl+C / EOF, re-raises so the outer
        handler in add_mistake_interactive can abort cleanly.
        """
        try:
            return input(prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            raise

    def add_mistake_interactive(
        self, curriculum: Curriculum | None = None, level: str = "L1"
    ) -> None:
        """
        Interactively log a mistake.
        For L1 (MCQ mode): streamlined single-question, A/B/C answers.
        For L2/L3: free-text question description, answers, explanation.
        The subject and module are required: they are the curriculum values that
        tie a mistake to the material it belongs to.
        Exits gracefully if the user stops inputting (Ctrl+C / Ctrl+D).
        """
        saved = 0
        subject = ""
        module_name = ""
        try:
            print("\n" + "=" * 50)
            is_mcq = level.upper() == "L1"
            if is_mcq:
                print("  📝 Log a Mistake (MCQ)")
            else:
                print("  📝 Log a Mistake")
            print("=" * 50)

            module_name = ""
            if curriculum:
                subject, module_name = self._pick_subject_and_module(curriculum, level)
                if not subject or not module_name:
                    print("❌ A subject and module are required to log a mistake.")
                    return
            else:
                subject = self._prompt("Subject (e.g., FRA, Equity, Ethics): ").strip()
                if not subject:
                    print("❌ Subject cannot be empty")
                    return
                module_name = self._prompt(
                    "Module (e.g., Module 3: Fiscal Policy): "
                ).strip()
                if not module_name:
                    print("❌ Module cannot be empty - a mistake must belong to a module.")
                    return

            if is_mcq:
                first = True
                while True:
                    result = self._log_mcq(
                        subject, module_name, level, show_hint=first
                    )
                    first = False
                    if result == "finished":
                        break
                    if result == "saved":
                        saved += 1
            else:
                if self._log_freeform(subject, module_name, level):
                    saved += 1

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — current mistake was NOT saved.")
            if saved > 0:
                noun = "mistake" if saved == 1 else "mistakes"
                verb = "was" if saved == 1 else "were"
                label = _session_label(subject, module_name)
                suffix = f" ({label})" if label else ""
                print(f"  ℹ️  {saved} {noun} {verb} saved before aborting{suffix}.")
        else:
            # The session ended normally: state the subject, the module and how
            # many mistakes were added in this session. The full breakdown of
            # the mistake log lives in `cfa-prep mis`.
            noun = "mistake" if saved == 1 else "mistakes"
            label = _session_label(subject, module_name)
            suffix = f" for {label}" if label else ""
            print(f"\n✅ Session complete — {saved} {noun} saved{suffix}.")

    def _log_mcq(
        self,
        subject: str,
        module_name: str,
        level: str,
        show_hint: bool = True,
    ) -> str:
        """
        Log an L1 MCQ mistake with 3-option input.
        Enter `\\b` on any field to go back and re-enter the previous field.

        Parameters:
            show_hint: print the \\b navigation hint (only on the first entry)

        Returns one of:
            "finished" — user entered a blank question (stop the session)
            "skipped"  — question already logged, user chose not to re-add
            "saved"    — a mistake was saved
        """
        if show_hint:
            print("\n  (Enter \\b on any field to go back and edit the previous one)")
        module_label = f" [{module_name}]" if module_name else ""
        data: dict[str, str] = {}

        fields: list[tuple[str, str, bool]] = [
            # (key, prompt, uppercase?)
            ("question", f"Question text{module_label} (blank to finish): ", False),
            ("option_a", "  Enter the 3 answer options:\n    A: ", False),
            ("option_b", "    B: ", False),
            ("option_c", "    C: ", False),
            ("user_letter", "\nYour wrong answer (A/B/C): ", True),
            ("correct_letter", "Correct answer (A/B/C): ", True),
            ("explanation", "Explanation (optional): ", False),
        ]

        i = 0
        while i < len(fields):
            key, prompt, upper = fields[i]

            raw = self._prompt(prompt).strip()
            # Back command: return to the previous field (no-op on the first)
            if raw == r"\b":
                if i > 0:
                    i -= 1
                    print(f"  ⬅️ Back to: {fields[i][0]}")
                else:
                    print("  ⚠️ Already at the first field.")
                continue

            # Question field has special handling: blank = finish, plus duplicate check
            if key == "question":
                if not raw:
                    return "finished"
                if raw != data.get("question"):
                    # Re-enter duplicate check whenever the question text changes
                    if not self._confirm_duplicate(raw):
                        print("  ⏭️ Skipped — already logged.")
                        return "skipped"
                data["question"] = raw
                i += 1
                continue

            data[key] = raw.upper() if upper else raw
            i += 1

        question = data["question"]
        option_a, option_b, option_c = data["option_a"], data["option_b"], data["option_c"]
        user_letter, correct_letter = data["user_letter"], data["correct_letter"]

        # Map letters to option text so the machine can identify the answer
        # regardless of display order (quiz can shuffle options later).
        letter_to_text = {"A": option_a, "B": option_b, "C": option_c}
        user_answer = letter_to_text.get(user_letter, user_letter)
        correct_answer = letter_to_text.get(correct_letter, correct_letter)

        explanation = data["explanation"]

        filepath = self.add_mistake(
            subject=subject,
            question=question,
            options=[option_a, option_b, option_c],
            user_answer=user_answer,
            correct_answer=correct_answer,
            explanation=explanation,
            module_name=module_name,
            level=level,
        )
        print(f"\n✅ Mistake saved to: {filepath}")
        return "saved"

    def _log_freeform(self, subject: str, module_name: str, level: str = "L1") -> bool:
        """
        Log an L2/L3 free-form mistake. Enter `\\b` on any single-line field to go
        back and re-enter the previous field. Returns True if a mistake was saved.
        """
        print("\n  (Enter \\b on any field to go back and edit the previous one)")
        data: dict[str, str] = {}

        # Question is multi-line (blank line to finish); other fields are single-line.
        fields: list[str] = [
            "user_answer",
            "correct_answer",
            "explanation",
        ]

        # 1. Multi-line question (first field; blank finishes the session)
        print("\nEnter the question description (enter a blank line to finish):")
        while True:
            lines = [self._prompt()]
            if lines[0] == "":
                print("  Cancelled.")
                return False
            while True:
                line = self._prompt()
                if line == "":
                    break
                lines.append(line)
            question = "\n".join(lines).strip()
            if not question:
                print("  Cancelled.")
                return False
            # Warn if this question was logged before, and let the user opt out
            if self._confirm_duplicate(question):
                data["question"] = question
                break
            print("  ⏭️ Skipped — already logged. Enter a different question.")

        # 2. Remaining single-line fields, with \b back navigation
        i = 0
        while i < len(fields):
            key = fields[i]
            if key == "user_answer":
                prompt = "\nYour wrong answer: "
            elif key == "correct_answer":
                prompt = "Correct answer: "
            else:
                prompt = "Explanation (one-sentence summary): "

            raw = self._prompt(prompt).strip()
            if raw == r"\b":
                if i > 0:
                    i -= 1
                    print(f"  ⬅️ Back to: {fields[i]}")
                else:
                    print("  ⚠️ Already at the first field.")
                continue
            data[key] = raw
            i += 1

        filepath = self.add_mistake(
            subject=subject,
            question=data["question"],
            user_answer=data["user_answer"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            module_name=module_name,
            level=level,
        )
        print(f"\n✅ Mistake saved to: {filepath}")
        return True

    @staticmethod
    def _pick_subject_and_module(curriculum: Curriculum, level: str) -> tuple[str, str]:
        """
        Browse the curriculum to pick a subject and module.
        Returns (subject, module_name) or ("", "") if the user aborts.
        """
        # 1. Pick subject
        subjects = curriculum.all_subjects(level)
        if not subjects:
            print("Curriculum is empty. Use free-text subject entry instead.")
            return "", ""

        print("\nPick a subject:")
        for i, s in enumerate(subjects, 1):
            print(f"  [{i}] {s}")
        choice = input("  > ").strip()
        if not choice.isdigit():
            return "", ""
        idx = int(choice) - 1
        if idx < 0 or idx >= len(subjects):
            return "", ""
        subject = subjects[idx]

        # 2. Pick module
        modules = curriculum.all_modules(level, subject)
        if not modules:
            print(f"No modules in {subject}.")
            return subject, ""

        print(f"\n  {subject} — pick a module:")
        for i, m in enumerate(modules, 1):
            print(f"    [{i}] {m}")
        choice = input("  > ").strip()
        if not choice.isdigit():
            return subject, ""
        idx = int(choice) - 1
        if idx < 0 or idx >= len(modules):
            return subject, ""
        module_name = modules[idx]

        return subject, module_name

    def get_recent_mistakes(self, limit: int = 10) -> list[MistakeRecord]:
        """
        Get the most recent N mistake records.
        Sorted by date in descending order.
        """
        records = self._load()
        records.sort(key=lambda r: r.get("date", ""), reverse=True)
        return records[:limit]

    def all_mistakes(self) -> list[MistakeRecord]:
        """Return every mistake record, as stored."""
        return self._load()

    def print_mistake_breakdown(self) -> None:
        """
        Print the mistake log grouped by subject and module, in curriculum order.

        A mistake belongs to a module, and the module is what the quiz reviews,
        so this is the breakdown that says what is still weak.  The curriculum is
        the source of truth for the order of the exam, so the summary follows it:
        the subjects in curriculum order, and inside a subject the modules in
        curriculum order.  This is the full summary shown by `cfa-prep mis`.
        """
        stats = self.get_mistake_stats()
        total_value = stats.get("total")
        total = total_value if isinstance(total_value, int) else 0
        modules_value = stats.get("modules")
        modules = (
            cast(dict[str, int], modules_value)
            if isinstance(modules_value, dict)
            else {}
        )
        if not modules:
            return
        noun = "mistake" if total == 1 else "mistakes"
        print_section(f"Mistake log by subject and module ({total} {noun})")
        subject_rank, module_rank = self._curriculum_order()
        ordered = sorted(
            modules.items(),
            key=lambda item: self._group_key(item[0], subject_rank, module_rank),
        )
        width = max(len(str(count)) for _group, count in ordered)
        for group, count in ordered:
            print(f"  {count:>{width}} — {group}")

    @staticmethod
    def _curriculum_order() -> tuple[dict[str, int], dict[str, dict[str, int]]]:
        """
        Return the curriculum position of every subject and module.

        The first value maps a subject to its rank, the second maps a subject to
        the rank of its modules.  A subject or module that is not part of the
        curriculum has no rank and ends up at the end of the list.
        """
        data = Curriculum().load()
        subject_rank: dict[str, int] = {}
        module_rank: dict[str, dict[str, int]] = {}
        for level in sorted(data.keys()):
            for subject, modules in data[level].items():
                if subject not in subject_rank:
                    subject_rank[subject] = len(subject_rank)
                    module_rank[subject] = {}
                ranks = module_rank[subject]
                for module in modules:
                    if module not in ranks:
                        ranks[module] = len(ranks)
        return subject_rank, module_rank

    @staticmethod
    def _group_key(
        group: str,
        subject_rank: dict[str, int],
        module_rank: dict[str, dict[str, int]],
    ) -> tuple[int, int, str]:
        """
        Return the sort key of a "Subject > Module" group in curriculum order.

        Groups that the curriculum does not know are sorted last, alphabetically.
        """
        subject, _, module = group.partition(" > ")
        subject_key = subject_rank.get(subject, len(subject_rank))
        ranks = module_rank.get(subject, {})
        module_key = ranks.get(module, len(ranks))
        return (subject_key, module_key, group)

    def get_mistake_stats(self) -> dict[str, object]:
        """
        Get mistake statistics.
        Returns the total count, per-subject counts, and per-module counts.
        """
        records = self._load()
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "subjects": {},
                "modules": {},
            }

        subj_count: dict[str, int] = {}
        module_count: dict[str, int] = {}
        for r in records:
            subj = r.get("subject", "Unknown")
            subj_count[subj] = subj_count.get(subj, 0) + 1
            module = r.get("module", "")
            if module:
                key = f"{subj} > {module}"
                module_count[key] = module_count.get(key, 0) + 1

        return {
            "total": total,
            "subjects": subj_count,
            "modules": module_count,
        }

    def list_mistake_files(self) -> list[Path]:
        """List the mistakes data file if it exists."""
        if self.data_file.exists():
            return [self.data_file]
        return []
