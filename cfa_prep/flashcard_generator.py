# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Manual flashcard module
Author: CodeBuddy AI Assistant
Purpose: Manually add Q&A flashcards, optionally selecting the subject/module
         from the curriculum, and store them at data/flashcards/flashcards.json.
"""

from pathlib import Path
from typing import cast

from .utils import (
    get_data_dir,
    write_file_text,
    today_str,
    load_json,
    save_json,
)
from .curriculum import Curriculum


class FlashcardGenerator:
    """
    Flashcard manager.
    Manages manually-added Q&A flashcards stored in a single JSON file.
    """

    def __init__(self):
        self.flashcards_dir: Path = get_data_dir("flashcards")
        self.manual_file: Path = self.flashcards_dir / "flashcards.json"
        self.curriculum: Curriculum = Curriculum()

    # --- manual flashcards ------------------------------------------------

    def _load_manual(self) -> list[dict[str, str]]:
        """Load the manually-added flashcards."""
        data = load_json(self.manual_file)
        return cast(list[dict[str, str]], data.get("cards", []))

    def _save_manual(self, cards: list[dict[str, str]]) -> None:
        """Save the manually-added flashcards."""
        save_json(self.manual_file, {"cards": cards})

    def add_manual(
        self,
        question: str,
        answer: str,
        level: str = "L1",
        subject: str = "",
        module: str = "",
    ) -> str:
        """
        Add a manually-created flashcard and persist it to flashcards.json.

        Parameters:
            question: the flashcard front (question)
            answer: the flashcard back (answer)
            level: exam level (L1/L2/L3)
            subject: subject from the curriculum (optional)
            module: module within the subject (optional)

        Returns:
            the path of the manual flashcard file
        """
        cards = self._load_manual()
        cards.append({
            "date": today_str(),
            "level": level,
            "subject": subject,
            "module": module,
            "question": question,
            "answer": answer,
        })
        self._save_manual(cards)
        return str(self.manual_file)

    def export_manual_markdown(self) -> str:
        """
        Export the manually-added flashcards to a Markdown file in the flashcards dir.
        """
        cards = self._load_manual()
        if not cards:
            return ""
        out_path = self.flashcards_dir / f"{today_str()}_manual_flashcards.md"
        lines = [f"# Manual CFA Flashcards\n", f"> Generated: {today_str()}\n\n"]
        for i, card in enumerate(cards, 1):
            location = " / ".join(
                part for part in (card.get("subject", ""), card.get("module", "")) if part
            )
            lines.append(f"## Flashcard {i}\n")
            lines.append(f"**Q**: {card['question']}\n\n")
            lines.append(f"**A**: {card['answer']}\n\n")
            if location:
                lines.append(f"*Location: {location}*\n\n")
            lines.append("---\n\n")
        write_file_text(out_path, "".join(lines))
        return str(out_path)

    @staticmethod
    def _prompt(prompt: str = "") -> str:
        """Read a line of input, raising on Ctrl+C / EOF so the caller can abort cleanly."""
        try:
            return input(prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            raise

    def _pick_subject_and_module(
        self, level: str = "L1"
    ) -> tuple[str, str] | None:
        """
        Browse the curriculum to pick a subject and module.
        Returns (subject, module), or None if the user finishes (blank subject),
        or ("", "") if the curriculum is empty.
        """
        subjects = self.curriculum.all_subjects(level)
        if not subjects:
            print("\n  ℹ️  Curriculum is empty — skipping subject/module selection.")
            return "", ""

        print("\n  Pick a subject (blank to finish):")
        for i, s in enumerate(subjects, 1):
            print(f"    [{i}] {s}")
        choice = self._prompt("  > ").strip()
        if not choice.isdigit():
            return None
        idx = int(choice) - 1
        if idx < 0 or idx >= len(subjects):
            return None
        subject = subjects[idx]

        modules = self.curriculum.all_modules(level, subject)
        if not modules:
            print(f"\n  ❌ No modules in {subject} — cannot add a card without a module.")
            return None

        print(f"\n  {subject} — pick a module (blank to finish):")
        for i, m in enumerate(modules, 1):
            print(f"    [{i}] {m}")
        choice = self._prompt("  > ").strip()
        if not choice.isdigit():
            return None
        idx = int(choice) - 1
        if idx < 0 or idx >= len(modules):
            return None
        return subject, modules[idx]

    def manual_flashcard(self, level: str = "L1") -> None:
        """
        Interactively add one or more flashcards by hand, optionally selecting
        the subject and module from the curriculum. Aborts cleanly on Ctrl+C/Ctrl+D.
        """
        added = 0
        try:
            print("\n" + "=" * 50)
            print("  🃏 Add Manual Flashcard")
            print("=" * 50)

            while True:
                picked = self._pick_subject_and_module(level)
                if picked is None:
                    break
                subject, module = picked
                location = " / ".join(p for p in (subject, module) if p)

                question = self._prompt(
                    f"\nQuestion{(' [' + location + ']') if location else ''} (blank to finish): "
                ).strip()
                if not question:
                    break

                answer = self._prompt("Answer: ").strip()
                if not answer:
                    print("  ❌ Answer cannot be empty — skipping this card.")
                    continue

                filepath = self.add_manual(
                    question=question,
                    answer=answer,
                    level=level,
                    subject=subject,
                    module=module,
                )
                added += 1
                print(f"  ✅ Saved to: {filepath}\n")

            noun = "flashcard" if added == 1 else "flashcards"
            print(f"\n  ✅ Finished adding {added} {noun}.")

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — current flashcard was NOT saved.")
            if added > 0:
                noun = "flashcard" if added == 1 else "flashcards"
                print(f"  ℹ️  {added} {noun} were added before aborting.")

    # --- viewing flashcards ------------------------------------------------

    def _pick_subject_filter(self, level: str = "L1") -> str:
        """
        Optionally pick a subject to filter by (blank to show all).
        Returns the subject name, or "" for all subjects.
        """
        subjects = self.curriculum.all_subjects(level)
        if not subjects:
            return ""
        print("\n  Filter by subject (blank for all):")
        for i, s in enumerate(subjects, 1):
            print(f"    [{i}] {s}")
        print("    [0] All")
        choice = self._prompt("  > ").strip()
        if not choice.isdigit():
            return ""
        idx = int(choice) - 1
        if idx < 0 or idx >= len(subjects):
            return ""
        return subjects[idx]

    def view_flashcards(self, level: str = "L1") -> None:
        """
        Interactively review flashcards: show each question, then reveal its
        answer or skip to the next card. Optionally filter by subject.
        Aborts cleanly on Ctrl+C/Ctrl+D.
        """
        try:
            print("\n" + "=" * 50)
            print("  🃏 Review Flashcards")
            print("=" * 50)

            cards = self._load_manual()
            if not cards:
                print("\n  No flashcards yet. Add some with 'cfa-prep flashcard --add'.")
                return

            subject = self._pick_subject_filter(level)
            if subject:
                filtered = [c for c in cards if c.get("subject") == subject]
                if not filtered:
                    print(f"\n  No flashcards for subject: {subject}")
                    return
                cards = filtered

            total = len(cards)
            print(f"\n  {total} flashcard(s). [Enter] to reveal answer, [n] next, [q] quit.\n")

            i = 0
            while i < total:
                card = cards[i]
                location = " / ".join(
                    part for part in (card.get("subject", ""), card.get("module", "")) if part
                )
                print(f"{'─' * 50}")
                print(f"  [{i + 1}/{total}] Q: {card['question']}\n")
                action = self._prompt("  [Enter] reveal answer, [n] next, [q] quit: ").strip().lower()

                if action == "q":
                    break
                if action == "n":
                    i += 1
                    continue

                # Reveal the answer (and the card's subject/module location)
                print(f"  A: {card['answer']}")
                if location:
                    print(f"      ({location})")
                print()
                action = self._prompt("  [Enter] next, [b] back, [q] quit: ").strip().lower()
                if action == "q":
                    break
                if action == "b":
                    if i > 0:
                        i -= 1
                    continue
                i += 1

            print("\n  ✅ Finished reviewing flashcards.")

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted.")
