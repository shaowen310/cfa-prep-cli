# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Progress tracking module
Author: CodeBuddy AI Assistant
Purpose: Store and display study progress as structured JSON at
         <data_root>/progress/progress.json.
         Tracks mastered and fuzzy knowledge points, mistake distribution,
         and next-day task suggestions.
"""

import json
import re
from pathlib import Path
from typing import TypedDict

from .utils import (
    get_data_dir,
    load_json,
    save_json,
    today_iso,
)


class ProgressData(TypedDict):
    """JSON shape of the progress file."""
    updated: str
    mastered: list[str]
    fuzzy: list[str]
    mistake_distribution: dict[str, float]


class ProgressTracker:
    """
    Progress tracker.
    Manages the study progress file (JSON), records mastered and fuzzy
    knowledge points, as well as daily review tasks.
    """

    def __init__(self) -> None:
        self.progress_dir: Path = get_data_dir("progress")
        self.progress_file: Path = self.progress_dir / "progress.json"

    # --- persistence -------------------------------------------------------

    def load(self) -> ProgressData:
        """
        Load the progress JSON, returning a default empty structure if the
        file does not exist yet.
        """
        data = load_json(self.progress_file)
        if not data:
            return ProgressData(
                updated=today_iso(),
                mastered=[],
                fuzzy=[],
                mistake_distribution={},
            )
        return ProgressData(
            updated=data.get("updated", today_iso()),
            mastered=data.get("mastered", []),
            fuzzy=data.get("fuzzy", []),
            mistake_distribution=data.get("mistake_distribution", {}),
        )

    def save(self, data: ProgressData) -> None:
        """Persist progress data to progress.json."""
        save_json(self.progress_file, dict(data))

    def get_mastered(self) -> list[str]:
        return self.load().get("mastered", [])

    def get_fuzzy(self) -> list[str]:
        return self.load().get("fuzzy", [])

    # --- update ------------------------------------------------------------

    def update(
        self,
        mastered: list[str] | None = None,
        fuzzy: list[str] | None = None,
        mistake_stats: dict[str, object] | None = None,
    ) -> None:
        """
        Update the progress file.

        Parameters:
            mastered: list of mastered knowledge point labels
            fuzzy: list of still-fuzzy knowledge point labels
            mistake_stats: mistake statistics (from MistakeAnalyzer.get_mistake_stats())
        """
        mastered = mastered or []
        fuzzy = fuzzy or []
        mistake_stats = mistake_stats or {}

        # Merge mastered: append new, deduplicate
        current = self.load()
        current_mastered = current.get("mastered", [])
        for item in mastered:
            if item not in current_mastered:
                current_mastered.append(item)

        # Merge fuzzy: append new, deduplicate
        current_fuzzy = current.get("fuzzy", [])
        for item in fuzzy:
            if item not in current_fuzzy:
                current_fuzzy.append(item)

        cats_value = mistake_stats.get("categories", {}) or {}
        cats: dict[str, float] = cats_value if isinstance(cats_value, dict) else {}

        data = ProgressData(
            updated=today_iso(),
            mastered=current_mastered,
            fuzzy=current_fuzzy,
            mistake_distribution=cats,
        )
        self.save(data)

    def remove_entries(self, indices: set[int]) -> int:
        """
        Remove entries at the given zero-based indices from the combined
        (mastered + fuzzy) list.  Returns the number of entries removed.
        """
        data = self.load()
        mastered = data.get("mastered", [])
        fuzzy = data.get("fuzzy", [])
        all_entries = [(True, e) for e in mastered] + [(False, e) for e in fuzzy]
        keep_mastered = [
            e for i, (is_m, e) in enumerate(all_entries)
            if not (is_m and i in indices)
        ]
        keep_fuzzy = [
            e for i, (is_m, e) in enumerate(all_entries)
            if not (is_m or i in indices)
        ]
        removed = len(mastered) + len(fuzzy) - len(keep_mastered) - len(keep_fuzzy)
        data["mastered"] = keep_mastered
        data["fuzzy"] = keep_fuzzy
        data["updated"] = today_iso()
        self.save(data)
        return removed

    # --- display -----------------------------------------------------------

    def show(self) -> None:
        """Display the raw JSON progress in the terminal."""
        data = self.load()
        print(json.dumps(data, indent=2, ensure_ascii=False))

    def display_structured(self, level: str = "L1", curriculum=None) -> None:
        """
        Display the current progress grouped by subject (chapter) and module,
        using the curriculum data model for the grouping hierarchy and topic lookup.
        Falls back to regex label parsing if no curriculum is provided.
        """
        data = self.load()
        mastered_entries = data.get("mastered", [])
        fuzzy_entries = data.get("fuzzy", [])
        updated = data.get("updated", today_iso())

        print(f"  Level: {level}")
        print(f"  Updated: {updated}")

        self._print_grouped("✅ Mastered", mastered_entries, curriculum, level)
        self._print_grouped("⚠️  Still Fuzzy", fuzzy_entries, curriculum, level)

    @staticmethod
    def _label_to_topic(label: str) -> str:
        """
        Extract the plain topic from a "[Subject > Module] Topic" label.
        Returns the portion after "] " or the full label if unparseable.
        """
        idx = label.rfind("] ")
        if idx != -1:
            return label[idx + 2:]
        return label

    @classmethod
    def _print_grouped(
        cls, title: str, entries: list[str], curriculum, level: str
    ) -> None:
        """Print entries grouped by subject → module, using the curriculum's data model."""
        print(f"\n  {title} ({len(entries)}):")

        if not entries:
            return

        if curriculum:
            cls._print_grouped_from_curriculum(entries, curriculum, level)
        else:
            cls._print_grouped_from_labels(entries)

    @classmethod
    def _print_grouped_from_curriculum(
        cls, entries: list[str], curriculum, level: str
    ) -> None:
        """
        Group progress entries using the curriculum's data model and print
        the full hierarchy — every subject and module from the curriculum is
        shown, even those with zero progress entries.
        """
        # Build {topic_str: (subject, module)} lookup from curriculum
        topic_to_meta: dict[str, tuple[str, str]] = {}
        for subject, modules in curriculum.subject_modules(level).items():
            for module, topics in modules.items():
                for t in topics:
                    topic_to_meta[t.lower()] = (subject, module)

        # Map progress entries to their (subject, module) via curriculum lookup
        entry_by_subject_module: dict[str, dict[str, list[str]]] = {}
        unparsed: list[str] = []
        for entry in entries:
            topic = cls._label_to_topic(entry).strip().lower()
            if topic in topic_to_meta:
                subject, module = topic_to_meta[topic]
                entry_by_subject_module.setdefault(subject, {}).setdefault(module, []).append(entry)
            else:
                unparsed.append(entry)

        # Print the full curriculum hierarchy, with progress counts per module.
        # Auto-collapse: if all topics in a module are in the list, hide the
        # topic details and show a ✓ marker.  Same for subjects.
        all_subjects = curriculum.subject_modules(level)
        for subject in sorted(all_subjects):
            curriculum_modules = all_subjects[subject]
            progress_modules = entry_by_subject_module.get(subject, {})
            done_count = sum(len(ts) for ts in progress_modules.values())
            total_count = sum(len(ts) for ts in curriculum_modules.values())
            # Collapse subject if every module is fully complete
            subject_complete = (
                total_count > 0
                and all(
                    len(progress_modules.get(m, [])) == len(curriculum_modules[m])
                    for m in curriculum_modules
                )
            )
            marker = " ✅" if subject_complete else ""
            print(f"    📖 {subject} ({done_count}/{total_count}){marker}")
            if subject_complete:
                continue
            for module in sorted(curriculum_modules):
                progress_topics = progress_modules.get(module, [])
                module_total = len(curriculum_modules[module])
                module_complete = progress_topics and len(progress_topics) == module_total
                if module_complete:
                    print(f"        ⤷ {module} ✅ ({len(progress_topics)}/{module_total})")
                elif progress_topics:
                    print(f"        ⤷ {module} ({len(progress_topics)}/{module_total}):")
                    for entry in sorted(progress_topics):
                        topic = cls._label_to_topic(entry)
                        print(f"            • {topic}")
                else:
                    print(f"        ⤷ {module} (0/{module_total})")

        if unparsed:
            print(f"    📝 Not in curriculum:")
            for entry in sorted(unparsed):
                print(f"        • {cls._label_to_topic(entry)}")

    @classmethod
    def _print_grouped_from_labels(cls, entries: list[str]) -> None:
        """Fallback: parse labels with regex and group by subject → module."""
        grouped: dict[str, dict[str, list[str]]] = {}
        unparsed: list[str] = []
        for entry in entries:
            m = re.match(r"^\[(.+?) > (.+?)\]\s+(.+)$", entry)
            if m:
                subject, module, topic = m.group(1), m.group(2), m.group(3)
                grouped.setdefault(subject, {}).setdefault(module, []).append(topic)
            else:
                unparsed.append(entry)

        for subject in sorted(grouped):
            modules = grouped[subject]
            topic_count = sum(len(ts) for ts in modules.values())
            print(f"    📖 {subject} ({topic_count} topics)")
            for module in sorted(modules):
                print(f"        ⤷ {module} ({len(modules[module])}):")
                for topic in sorted(modules[module]):
                    print(f"            • {topic}")

        if unparsed:
            print(f"    📝 Uncategorized:")
            for entry in unparsed:
                print(f"        • {cls._label_to_topic(entry)}")

    # --- interactive -------------------------------------------------------

    def interactive_update(
        self,
        mistake_stats: dict[str, object] | None = None,
        curriculum=None,
        level: str = "L1",
    ) -> None:
        """
        Interactively update the progress.
        Supports free-text entry (module names, topic names) and browsing
        the curriculum to select topics by number.
        If the user aborts (Ctrl+C), progress is NOT saved.
        """
        print("\n" + "=" * 50)
        print("  📊 Update Study Progress")
        print("=" * 50)

        try:
            print("\nEnter mastered knowledge points (one per line, blank line to finish):")
            print("  • Type a topic or module name, or `?` to browse the curriculum.")
            mastered: list[str] = self._collect_entries(curriculum, level)

            print("\nEnter fuzzy knowledge points (one per line, blank line to finish):")
            print("  • Type a topic or module name, or `?` to browse the curriculum.")
            fuzzy: list[str] = self._collect_entries(curriculum, level)

            self.update(
                mastered=mastered,
                fuzzy=fuzzy,
                mistake_stats=mistake_stats,
            )
            print(f"\n✅ Progress updated to: {self.progress_file}")
        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — progress was NOT saved.")

    def _collect_entries(self, curriculum, level: str) -> list[str]:
        """Collect progress entries line by line; `?` enters curriculum browse mode."""
        entries: list[str] = []
        while True:
            line = input("  > ").strip()
            if line == "":
                break
            if line == "?" and curriculum:
                picked = self._browse_curriculum(curriculum, level)
                entries.extend(picked)
            else:
                results = self._validate_entry(line, curriculum, level)
                entries.extend(results)
        return entries

    @staticmethod
    def _browse_curriculum(curriculum, level: str) -> list[str]:
        """
        Interactive curriculum browser: pick subject → module → topics.
        Returns a list of "[Subject > Module] Topic" labels for selected topics.
        """
        # 1. Pick subject
        subjects = curriculum.all_subjects(level)
        if not subjects:
            print("     Curriculum is empty.")
            return []

        print("\n     Pick a subject:")
        for i, s in enumerate(subjects, 1):
            print(f"       [{i}] {s}")
        choice = input("     > ").strip()
        if not choice.isdigit():
            return []
        idx = int(choice) - 1
        if idx < 0 or idx >= len(subjects):
            return []
        subject = subjects[idx]

        # 2. Pick module(s)
        modules = curriculum.all_modules(level, subject)
        if not modules:
            print(f"     No modules in {subject}.")
            return []

        print(f"\n     {subject} — pick module(s) (space-separated numbers, or 'all'):")
        for i, m in enumerate(modules, 1):
            print(f"       [{i}] {m}")
        choice = input("     > ").strip().lower()

        if choice == "all":
            picked_modules = list(range(len(modules)))
        else:
            picked_modules = [int(n) - 1 for n in choice.split() if n.isdigit()]
        if not picked_modules:
            return []

        # 3. For each selected module, ask: all topics or pick individually?
        results: list[str] = []
        data = curriculum.subject_modules(level)
        subject_modules = data.get(subject, {})
        for mi in picked_modules:
            if mi < 0 or mi >= len(modules):
                continue
            module = modules[mi]
            topics = subject_modules.get(module, [])
            if not topics:
                continue

            print(f"\n     📁 {module} ({len(topics)} topics)")
            print(f"       Add all? [y]es / [n]o (pick individually) / [s]kip")
            choice = input("     > ").strip().lower()

            if choice == "s" or choice == "skip":
                continue

            if choice == "n" or choice == "no":
                # Show individual topics to pick
                print(f"       Pick topic(s) (space-separated numbers, or 'all'):")
                for i, t in enumerate(topics, 1):
                    print(f"         [{i}] {t}")
                pick = input("       > ").strip().lower()
                if pick == "all":
                    for t in topics:
                        label = f"[{subject} > {module}] {t}"
                        results.append(label)
                        print(f"         ↳ {t}")
                else:
                    for n in pick.split():
                        if n.isdigit():
                            ti = int(n) - 1
                            if 0 <= ti < len(topics):
                                t = topics[ti]
                                label = f"[{subject} > {module}] {t}"
                                results.append(label)
                                print(f"         ↳ {t}")
            else:
                # Default: add all
                for t in topics:
                    label = f"[{subject} > {module}] {t}"
                    results.append(label)
                    print(f"       ↳ {t}")
        print(f"     → Added {len(results)} topics total.")
        return results

    @staticmethod
    def _validate_entry(text: str, curriculum, level: str) -> list[str]:
        """
        Validate a free-text progress entry against the curriculum.

        Resolution order:
          1. Module name → expands to all "[Subject > Module] Topic" labels for that module.
          2. Topic label or topic text → matches a single curriculum label.
          3. No match → rejected (not added to progress).

        Returns a list of validated entry strings (usually one, or many for a module).
        """
        if not curriculum:
            return [text]

        # 1. Try module name expansion
        module_topics = curriculum.resolve_module(text, level)
        if module_topics:
            print(f"     ↳ Module '{text}' → added {len(module_topics)} topics")
            return module_topics

        # 2. Try single topic/label match
        resolved = curriculum.resolve_label(text, level)
        if resolved and resolved.lower() != text.lower():
            print(f"     ↳ Corrected to: {resolved}")
            return [resolved]
        if resolved:
            return [resolved]

        # 3. No match; reject
        print(f"     ❌ Not in curriculum — skipped.")
        return []

    def remove_interactive(self) -> None:
        """
        Interactively remove entries from mastered or fuzzy lists.
        Lists all entries with indices and lets the user select which to delete.
        """
        data = self.load()
        mastered = data.get("mastered", [])
        fuzzy = data.get("fuzzy", [])

        if not mastered and not fuzzy:
            print("No progress entries to remove.")
            return

        all_entries: list[tuple[str, str]] = []
        if mastered:
            print("\n  ✅ Mastered:")
            for i, entry in enumerate(mastered, 1):
                print(f"    [{i}] {self._label_to_topic(entry)}")
                all_entries.append(("mastered", entry))
        master_count = len(mastered)

        if fuzzy:
            print("\n  ⚠️  Still Fuzzy:")
            for i, entry in enumerate(fuzzy, master_count + 1):
                print(f"    [{i}] {self._label_to_topic(entry)}")
                all_entries.append(("fuzzy", entry))

        print("\n  Enter the numbers to remove (space-separated, e.g. 1 3 5):")
        choice = input("  > ").strip()
        if not choice:
            print("  Cancelled.")
            return

        try:
            indices = {int(n) - 1 for n in choice.split()}
        except ValueError:
            print("❌ Invalid input. Please enter numbers separated by spaces.")
            return

        if not indices or max(indices) >= len(all_entries):
            print("❌ One or more numbers are out of range.")
            return

        removed = self.remove_entries(indices)
        print(f"✅ Removed {removed} entr{'y' if removed == 1 else 'ies'}.")
        print(f"   Updated: {self.progress_file}")

    # --- quiz support ------------------------------------------------------

    def get_key_points_to_review(self) -> list[str]:
        """
        Return the still-fuzzy knowledge points that need review.
        """
        return self.get_fuzzy()
