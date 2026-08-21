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
    today_str,
    load_json,
    save_json,
)
from .curriculum import Curriculum


class MistakeRecord(TypedDict):
    date: str
    level: str
    subject: str
    module: str
    question: str
    options: list[str]  # [A text, B text, C text]
    user_answer: str     # the option text the user chose
    correct_answer: str  # the option text that is correct
    key_point: str
    correct_conclusion: str
    source: str


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
            if r.get("key_point"):
                print(f"      📌 Key point: {r['key_point']}")
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
        key_point: str,
        correct_conclusion: str,
        source: str = "",
        module_name: str = "",
        level: str = "L1",
        options: list[str] | None = None,
    ) -> str:
        """
        Add a mistake record to mistakes.json.

        Parameters:
            subject: subject name (e.g., Economics)
            question: question text (without options)
            user_answer: the user's incorrect answer
            correct_answer: the correct answer
            key_point: knowledge point
            correct_conclusion: correct conclusion
            source: source reference
            module_name: module within the subject
            level: exam level (L1/L2/L3)
            options: list of option texts [A, B, C] for MCQ (optional)

        Returns:
            the path of the mistakes file
        """
        records = self._load()
        records.append(MistakeRecord(
            date=today_str(),
            level=level,
            subject=subject,
            module=module_name,
            question=question,
            options=options or [],
            user_answer=user_answer,
            correct_answer=correct_answer,
            key_point=key_point,
            correct_conclusion=correct_conclusion,
            source=source,
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
        For L1 (MCQ mode): streamlined single-question, A/B/C answers,
        key point picked from curriculum topics.
        For L2/L3: free-text question description, answers, key point, conclusion.
        Exits gracefully if the user stops inputting (Ctrl+C / Ctrl+D).
        """
        saved = 0
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
                if not subject:
                    return
            else:
                subject = self._prompt("Subject (e.g., FRA, Equity, Ethics): ").strip()
                if not subject:
                    print("❌ Subject cannot be empty")
                    return

            if is_mcq:
                while True:
                    result = self._log_mcq(subject, module_name, curriculum, level)
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
                print(f"  ℹ️  {saved} {noun} were saved before aborting.")

    def _log_mcq(
        self, subject: str, module_name: str, curriculum: Curriculum | None, level: str
    ) -> str:
        """
        Log an L1 MCQ mistake with 3-option input.
        Enter `\\b` on any field to go back and re-enter the previous field.

        Returns one of:
            "finished" — user entered a blank question (stop the session)
            "skipped"  — question already logged, user chose not to re-add
            "saved"    — a mistake was saved
        """
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
            ("key_point", "Key point (one-sentence summary): ", False),
            ("correct_conclusion", "Correct conclusion / explanation (optional): ", False),
        ]

        i = 0
        while i < len(fields):
            key, prompt, upper = fields[i]

            # Key point is picked from the curriculum menu (with \b handled inside)
            if key == "key_point":
                picked = self._pick_key_point(curriculum, level, subject, module_name)
                if picked == "__back__":
                    if i > 0:
                        i -= 1
                        print(f"  ⬅️ Back to: {fields[i][0]}")
                    continue
                data["key_point"] = picked
                i += 1
                continue

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

        key_point = data["key_point"]
        correct_conclusion = data["correct_conclusion"]

        filepath = self.add_mistake(
            subject=subject,
            question=question,
            options=[option_a, option_b, option_c],
            user_answer=user_answer,
            correct_answer=correct_answer,
            key_point=key_point,
            correct_conclusion=correct_conclusion,
            source=f"{subject} > {module_name}" if module_name else "",
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
            "key_point",
            "correct_conclusion",
            "source",
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
        default_source = f"{subject} > {module_name}" if module_name else ""
        i = 0
        while i < len(fields):
            key = fields[i]
            if key == "user_answer":
                prompt = "\nYour wrong answer: "
            elif key == "correct_answer":
                prompt = "Correct answer: "
            elif key == "key_point":
                prompt = "\nKey point (one-sentence summary): "
            elif key == "correct_conclusion":
                prompt = "Correct conclusion (one-sentence summary): "
            else:  # source
                prompt = f"Source [{default_source}]: "

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

        source = data["source"] or default_source

        filepath = self.add_mistake(
            subject=subject,
            question=data["question"],
            user_answer=data["user_answer"],
            correct_answer=data["correct_answer"],
            key_point=data["key_point"],
            correct_conclusion=data["correct_conclusion"],
            source=source,
            module_name=module_name,
            level=level,
        )
        print(f"\n✅ Mistake saved to: {filepath}")
        return True

    def _pick_key_point(
        self, curriculum: Curriculum | None, level: str, subject: str, module_name: str
    ) -> str:
        """
        Let the user pick the key point (topic) from the selected module's topics.
        Falls back to free-text if curriculum is unavailable or module has no topics.
        Returns "__back__" if the user enters `\\b` to go back to the previous field.
        """
        if not curriculum or not module_name:
            return self._prompt("Key point (one-sentence summary): ").strip()

        modules = cast(
            dict[str, dict[str, list[str]]], curriculum.subject_modules(level)
        )
        topics = modules.get(subject, {}).get(module_name, [])
        if not topics:
            return self._prompt("Key point (one-sentence summary): ").strip()

        print(f"\n  Pick the key point tested by this question:")
        for i, t in enumerate(topics, 1):
            print(f"    [{i}] {t}")
        print(f"    [0] Type a custom key point")
        print(f"    [\\b] Back to the previous field")
        choice = self._prompt("  > ").strip()
        if choice == r"\b":
            return "__back__"
        if choice == "0" or not choice.isdigit():
            return self._prompt("Key point (one-sentence summary): ").strip()

        idx = int(choice) - 1
        if 0 <= idx < len(topics):
            return topics[idx]
        return self._prompt("Key point (one-sentence summary): ").strip()

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

    def get_mistake_stats(self) -> dict[str, object]:
        """
        Get mistake statistics.
        Returns the total count, per-subject counts, and key points.
        """
        records = self._load()
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "subjects": {},
                "key_points": [],
            }

        subj_count: dict[str, int] = {}
        key_points: list[str] = []
        for r in records:
            subj = r.get("subject", "Unknown")
            subj_count[subj] = subj_count.get(subj, 0) + 1
            kp = r.get("key_point", "")
            if kp:
                key_points.append(kp)

        return {
            "total": total,
            "subjects": subj_count,
            "key_points": key_points,
        }

    def list_mistake_files(self) -> list[Path]:
        """List the mistakes data file if it exists."""
        if self.data_file.exists():
            return [self.data_file]
        return []
