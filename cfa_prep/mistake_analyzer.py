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

    def add_mistake_interactive(self) -> None:
        """
        Interactively log a mistake.
        Guides the user through entering mistake details step by step.
        Exits gracefully if the user stops inputting (Ctrl+C / Ctrl+D).
        """
        print("\n" + "=" * 50)
        print("  📝 Log a Mistake")
        print("=" * 50)

        subject = self._prompt("Subject (e.g., FRA, Equity, Ethics): ").strip()
        if not subject:
            print("❌ Subject cannot be empty")
            return

        print("\nEnter the question description (enter a blank line to finish):")
        question_lines = []
        while True:
            line = self._prompt()
            if line == "":  # blank line, or the user cancelled input (Ctrl+C / Ctrl+D)
                break
            question_lines.append(line)
        question = "\n".join(question_lines)
        if not question.strip():
            print("❌ Question cannot be empty")
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
        source = self._prompt("Source (e.g., @data/kb/l2_vol3_p120-180.txt (P145)): ").strip()

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
