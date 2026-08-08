# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Mistake analyzer module
Author: CodeBuddy AI Assistant
Purpose: Log and analyze mistakes, categorized into three types (concept confusion / calculation error / misreading),
         automatically written to the data/mistakes/ directory, and generate review suggestions.
"""

from pathlib import Path

from .utils import (
    get_data_dir,
    today_str,
    write_file_text,
    read_file_text,
    load_json,
    save_json,
)


# Mistake categories
MISTAKE_CATEGORIES = {
    "1": "Concept confusion",
    "2": "Calculation error",
    "3": "Misreading the question",
}


class MistakeAnalyzer:
    """
    Mistake analyzer.
    Manages the entry, categorization, storage, and retrieval of mistakes.
    """

    def __init__(self):
        self.mistakes_dir: Path = get_data_dir("mistakes")
        self.index_file: Path = self.mistakes_dir / "mistakes_index.json"
        self.index: dict[str, object] = load_json(self.index_file)

    def _save_index(self) -> None:
        """Save the mistake index"""
        save_json(self.index_file, self.index)

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
    ) -> str:
        """
        Add a mistake record.

        Parameters:
            subject: subject name (e.g., FRA, Equity, Ethics)
            question: question description
            user_answer: the user's incorrect answer
            correct_answer: the correct answer
            category: mistake category (Concept confusion / Calculation error / Misreading the question)
            key_point: knowledge point (one sentence)
            correct_conclusion: correct conclusion (one sentence)
            source: source (e.g., @data/kb/l2_vol3_p120-180.txt (P145))

        Returns:
            the path of the generated mistake file
        """
        date_str = today_str()
        category_short = category.replace(" ", "_")
        filename = f"{date_str}_{subject}_{category_short}.md"
        filepath = self.mistakes_dir / filename

        # Check if a mistake file for the same day already exists; if so, append
        existing = read_file_text(filepath)

        entry = f"""
### Mistake Record

**Date**: {date_str}
**Subject**: {subject}
**Category**: {category}
**Key point**: {key_point}
**Correct conclusion**: {correct_conclusion}
**Source**: {source if source else "(Not specified)"}

---

**Question**:
{question}

**My answer**: {user_answer}

**Correct answer**: {correct_answer}

---

"""
        if existing:
            write_file_text(filepath, existing + "\n" + entry)
        else:
            write_file_text(filepath, entry)

        # Update the index
        records = self.index.get("records")
        if not isinstance(records, list):
            records = []
            self.index["records"] = records
        records.append({
            "date": date_str,
            "subject": subject,
            "category": category,
            "key_point": key_point,
            "file": filename,
        })
        self._save_index()

        return str(filepath)

    @staticmethod
    def _prompt(prompt: str = "") -> str:
        """
        Safely read a line of input.
        Returns "" on Ctrl+C / EOF (Ctrl+D) so the caller can exit gracefully
        instead of raising a traceback.
        """
        try:
            return input(prompt)
        except (KeyboardInterrupt, EOFError):
            print("\n⚠️  Input cancelled.")
            return ""

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
                self._log_freeform(subject, module_name)

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — mistake was NOT saved.")

    def _log_mcq(
        self, subject: str, module_name: str, curriculum, level: str
    ) -> None:
        """Log an L1 MCQ mistake with streamlined input."""
        question = self._prompt("\nQuestion text: ").strip()
        if not question:
            print("  Cancelled.")
            return

        user_answer = self._prompt("Your answer (A/B/C): ").strip().upper()
        correct_answer = self._prompt("Correct answer (A/B/C): ").strip().upper()

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
            user_answer=user_answer,
            correct_answer=correct_answer,
            category=category,
            key_point=key_point,
            correct_conclusion=correct_conclusion,
            source=f"{subject} > {module_name}" if module_name else "",
        )
        print(f"\n✅ Mistake saved to: {filepath}")

    def _log_freeform(self, subject: str, module_name: str) -> None:
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

    def get_recent_mistakes(self, limit: int = 10) -> list[dict[str, object]]:
        """
        Get the most recent N mistake records.
        Sorted by date in descending order.
        """
        records = self.index.get("records", [])
        if not isinstance(records, list):
            return []

        dict_records: list[dict[str, object]] = [r for r in records if isinstance(r, dict)]
        dict_records.sort(key=lambda r: str(r.get("date", "")), reverse=True)
        return dict_records[:limit]

    def get_mistake_stats(self) -> dict[str, object]:
        """
        Get mistake statistics.
        Returns the count and percentage for each mistake category.
        """
        records = self.index.get("records", [])
        if not isinstance(records, list):
            return {
                "total": 0,
                "categories": {},
                "subjects": {},
                "key_points": [],
            }

        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "categories": {},
                "subjects": {},
                "key_points": [],
            }

        # Count the category distribution
        cat_count: dict[str, int] = {}
        for r in records:
            if not isinstance(r, dict):
                continue
            cat = str(r.get("category", "Uncategorized"))
            cat_count[cat] = cat_count.get(cat, 0) + 1

        cat_pct = {k: round(v / total * 100, 1) for k, v in cat_count.items()}

        # Count the subject distribution
        subj_count: dict[str, int] = {}
        for r in records:
            if not isinstance(r, dict):
                continue
            subj = str(r.get("subject", "Unknown"))
            subj_count[subj] = subj_count.get(subj, 0) + 1

        # Extract all knowledge points
        key_points = [str(r.get("key_point", "")) for r in records if isinstance(r, dict) and r.get("key_point")]

        return {
            "total": total,
            "categories": cat_pct,
            "subjects": subj_count,
            "key_points": key_points,
        }

    def list_mistake_files(self) -> list[Path]:
        """List all mistake files"""
        return sorted(
            [f for f in self.mistakes_dir.glob("*.md") if f.name != "mistakes_index.json"],
            reverse=True,
        )
