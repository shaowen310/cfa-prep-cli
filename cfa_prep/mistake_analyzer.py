# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Mistake analyzer module
Author: CodeBuddy AI Assistant
Purpose: Log and analyze mistakes, stored as JSON at <data_root>/mistakes/mistakes.json.
         Supports MCQ (L1) and free-form (L2/L3) mistake logging.
"""

from pathlib import Path
from typing import TypedDict

from .utils import (
    get_data_dir,
    today_str,
    load_json,
    save_json,
)


# Mistake categories
MISTAKE_CATEGORIES = {
    "1": "Concept confusion",
    "2": "Calculation error",
    "3": "Misreading the question",
}


class MistakeRecord(TypedDict):
    date: str
    level: str
    subject: str
    module: str
    question: str
    options: list[str]  # [A text, B text, C text]
    user_answer: str     # the option text the user chose
    correct_answer: str  # the option text that is correct
    category: str
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
        # At runtime these are dicts matching the MistakeRecord shape.
        return records  # type: ignore[return-value]

    def _save(self, records: list[MistakeRecord]) -> None:
        """Save all mistake records."""
        save_json(self.data_file, {"records": list(records)})

    def add_mistake(
        self,
        subject: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        category: str,
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
            category: mistake category
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
            category=category,
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
        self, curriculum=None, level: str = "L1"
    ) -> None:
        """
        Interactively log a mistake.
        For L1 (MCQ mode): streamlined single-question, A/B/C answers,
        key point picked from curriculum topics.
        For L2/L3: free-text question description, answers, key point, conclusion.
        Exits gracefully if the user stops inputting (Ctrl+C / Ctrl+D).
        """
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
                self._log_mcq(subject, module_name, curriculum, level)
            else:
                self._log_freeform(subject, module_name, level)

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — mistake was NOT saved.")

    def _log_mcq(
        self, subject: str, module_name: str, curriculum, level: str
    ) -> None:
        """Log an L1 MCQ mistake with 3-option input."""
        question = self._prompt("\nQuestion text: ").strip()
        if not question:
            print("  Cancelled.")
            return

        # Collect the 3 options
        print("\n  Enter the 3 answer options:")
        option_a = self._prompt("    A: ").strip()
        option_b = self._prompt("    B: ").strip()
        option_c = self._prompt("    C: ").strip()

        # Which one did the user pick?
        print("\n  Your answer was:")
        print(f"    [A] {option_a}")
        print(f"    [B] {option_b}")
        print(f"    [C] {option_c}")
        user_letter = self._prompt("  > ").strip().upper()

        correct_letter = self._prompt("\nCorrect answer (A/B/C): ").strip().upper()

        # Map letters to option text so the machine can identify the answer
        # regardless of display order (quiz can shuffle options later).
        letter_to_text = {"A": option_a, "B": option_b, "C": option_c}
        user_answer = letter_to_text.get(user_letter, user_letter)
        correct_answer = letter_to_text.get(correct_letter, correct_letter)

        print("\nMistake category:")
        for key, value in MISTAKE_CATEGORIES.items():
            print(f"  [{key}] {value}")
        cat_choice = self._prompt("Choose a mistake category (1/2/3): ").strip()
        category = MISTAKE_CATEGORIES.get(cat_choice, "Concept confusion")

        # Pick the key point from the module's topics
        key_point = self._pick_key_point(curriculum, level, subject, module_name)

        correct_conclusion = self._prompt(
            "Correct conclusion / explanation (optional): "
        ).strip()

        filepath = self.add_mistake(
            subject=subject,
            question=question,
            options=[option_a, option_b, option_c],
            user_answer=user_answer,
            correct_answer=correct_answer,
            category=category,
            key_point=key_point,
            correct_conclusion=correct_conclusion,
            source=f"{subject} > {module_name}" if module_name else "",
            module_name=module_name,
            level=level,
        )
        print(f"\n✅ Mistake saved to: {filepath}")

    def _log_freeform(self, subject: str, module_name: str, level: str = "L1") -> None:
        """Log an L2/L3 free-form mistake."""
        print("\nEnter the question description (enter a blank line to finish):")
        question_lines = []
        while True:
            line = self._prompt()
            if line == "":
                break
            question_lines.append(line)
        question = "\n".join(question_lines)
        if not question.strip():
            print("  Cancelled.")
            return

        user_answer = self._prompt("\nYour answer: ").strip()
        correct_answer = self._prompt("Correct answer: ").strip()

        print("\nMistake category:")
        for key, value in MISTAKE_CATEGORIES.items():
            print(f"  [{key}] {value}")
        cat_choice = self._prompt("Choose a mistake category (1/2/3): ").strip()
        category = MISTAKE_CATEGORIES.get(cat_choice, "Concept confusion")

        key_point = self._prompt("\nKey point (one-sentence summary): ").strip()
        correct_conclusion = self._prompt("Correct conclusion (one-sentence summary): ").strip()

        default_source = f"{subject} > {module_name}" if module_name else ""
        source = self._prompt(f"Source [{default_source}]: ").strip()
        if not source:
            source = default_source

        filepath = self.add_mistake(
            subject=subject,
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer,
            category=category,
            key_point=key_point,
            correct_conclusion=correct_conclusion,
            source=source,
            module_name=module_name,
            level=level,
        )
        print(f"\n✅ Mistake saved to: {filepath}")

    @staticmethod
    def _pick_key_point(curriculum, level: str, subject: str, module_name: str) -> str:
        """
        Let the user pick the key point (topic) from the selected module's topics.
        Falls back to free-text if curriculum is unavailable or module has no topics.
        """
        if not curriculum or not module_name:
            return input("Key point (one-sentence summary): ").strip()

        modules = curriculum.subject_modules(level)
        topics = modules.get(subject, {}).get(module_name, [])
        if not topics:
            return input("Key point (one-sentence summary): ").strip()

        print(f"\n  Pick the key point tested by this question:")
        for i, t in enumerate(topics, 1):
            print(f"    [{i}] {t}")
        print(f"    [0] Type a custom key point")
        choice = input("  > ").strip()
        if choice == "0" or not choice.isdigit():
            return input("Key point (one-sentence summary): ").strip()

        idx = int(choice) - 1
        if 0 <= idx < len(topics):
            return topics[idx]
        return input("Key point (one-sentence summary): ").strip()

    @staticmethod
    def _pick_subject_and_module(curriculum, level: str) -> tuple[str, str]:
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
        Returns the count and percentage for each mistake category.
        """
        records = self._load()
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "categories": {},
                "subjects": {},
                "key_points": [],
            }

        cat_count: dict[str, int] = {}
        subj_count: dict[str, int] = {}
        key_points: list[str] = []
        for r in records:
            cat = r.get("category", "Uncategorized")
            cat_count[cat] = cat_count.get(cat, 0) + 1
            subj = r.get("subject", "Unknown")
            subj_count[subj] = subj_count.get(subj, 0) + 1
            kp = r.get("key_point", "")
            if kp:
                key_points.append(kp)

        cat_pct = {k: round(v / total * 100, 1) for k, v in cat_count.items()}
        return {
            "total": total,
            "categories": cat_pct,
            "subjects": subj_count,
            "key_points": key_points,
        }

    def list_mistake_files(self) -> list[Path]:
        """List the mistakes data file if it exists."""
        if self.data_file.exists():
            return [self.data_file]
        return []
