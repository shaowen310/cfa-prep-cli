# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Progress tracking module
Author: CodeBuddy AI Assistant
Purpose: Maintain and update the data/progress/progress.md progress file,
         track mastered/still-fuzzy knowledge points, summarize mistake distribution, and generate next-day task suggestions.
"""

from pathlib import Path

from .utils import (
    get_data_dir,
    today_iso,
    write_file_text,
    read_file_text,
)


class ProgressTracker:
    """
    Progress tracker.
    Manages the study progress file, records mastered and fuzzy knowledge points,
    as well as daily review tasks.
    """

    def __init__(self) -> None:
        self.progress_dir: Path = get_data_dir("progress")
        self.progress_file: Path = self.progress_dir / "progress.md"

    def _get_default_content(self) -> str:
        """Generate the default progress file content"""
        return f"""# CFA Study Progress

> Progress overview (updated on {today_iso()})

## Mastered

(No records yet)

## Still Fuzzy

(No records yet)

## Mistake Distribution

(No data yet)

## Sole Task for Tomorrow

(No plan yet)
"""

    def load(self) -> str:
        """Read the current progress file content"""
        content = read_file_text(self.progress_file)
        if not content:
            content = self._get_default_content()
            write_file_text(self.progress_file, content)
        return content

    def update(
        self,
        mastered: list[str] | None = None,
        fuzzy: list[str] | None = None,
        mistake_stats: dict[str, object] | None = None,
        tomorrow_task: str = "",
    ) -> None:
        """
        Update the progress file.

        Parameters:
            mastered: list of mastered knowledge points
            fuzzy: list of still-fuzzy knowledge points
            mistake_stats: mistake statistics (from MistakeAnalyzer.get_mistake_stats())
            tomorrow_task: description of tomorrow's sole task
        """
        mastered = mastered or []
        fuzzy = fuzzy or []
        mistake_stats = mistake_stats or {}

        # Format mastered items
        mastered_str = "\n".join(f"- {item}" for item in mastered) if mastered else "(No records yet)"

        # Format still-fuzzy items
        fuzzy_str = "\n".join(f"- {item}" for item in fuzzy) if fuzzy else "(No records yet)"

        # Format mistake distribution
        cats_value = mistake_stats.get("categories", {}) or {}
        cats: dict[str, float] = cats_value if isinstance(cats_value, dict) else {}
        if cats:
            cat_lines = []
            for cat, pct in sorted(cats.items(), key=lambda item: float(item[1]), reverse=True):
                cat_lines.append(f"- {cat}: {pct}%")
            cat_str = "\n".join(cat_lines)
        else:
            cat_str = "(No data yet)"

        # Format tomorrow's task
        task_str = tomorrow_task if tomorrow_task else "(No plan yet)"

        content = f"""# CFA Study Progress

> Progress overview (updated on {today_iso()})

## Mastered

{mastered_str}

## Still Fuzzy

{fuzzy_str}

## Mistake Distribution

{cat_str}

## Sole Task for Tomorrow

{task_str}
"""
        write_file_text(self.progress_file, content)

    def show(self) -> None:
        """Display the current progress in the terminal"""
        content = self.load()
        print(content)

    def interactive_update(self, mistake_stats: dict[str, object] | None = None) -> None:
        """
        Interactively update the progress.
        Guides the user to enter mastered and fuzzy knowledge points.
        """
        print("\n" + "=" * 50)
        print("  📊 Update Study Progress")
        print("=" * 50)

        print("\nEnter the knowledge points you have mastered (one per line, blank line to finish):")
        mastered = []
        while True:
            line = input("  > ").strip()
            if line == "":
                break
            mastered.append(line)

        print("\nEnter the knowledge points still fuzzy (one per line, blank line to finish):")
        fuzzy = []
        while True:
            line = input("  > ").strip()
            if line == "":
                break
            fuzzy.append(line)

        tomorrow = input("\nSole task for tomorrow (optional): ").strip()

        self.update(
            mastered=mastered,
            fuzzy=fuzzy,
            mistake_stats=mistake_stats,
            tomorrow_task=tomorrow,
        )
        print(f"\n✅ Progress updated to: {self.progress_file}")

    def get_key_points_to_review(self) -> list[str]:
        """
        Extract the knowledge points that need review from the progress file.
        Returns the still-fuzzy knowledge points first.
        """
        content = self.load()
        fuzzy_points = []

        in_fuzzy = False
        for line in content.split("\n"):
            if line.startswith("## Still Fuzzy"):
                in_fuzzy = True
                continue
            if in_fuzzy and line.startswith("## "):
                break
            if in_fuzzy and line.strip().startswith("- "):
                point = line.strip()[2:].strip()
                if point and point != "(No records yet)":
                    fuzzy_points.append(point)

        return fuzzy_points
