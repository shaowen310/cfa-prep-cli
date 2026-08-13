# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Flashcard generator module
Author: CodeBuddy AI Assistant
Purpose: Extract key concepts from the knowledge base (data/kb/), generate Q&A flashcards,
         output to data/flashcards/, support per-subject files and export to Anki-compatible CSV.
"""

import re
import csv
from pathlib import Path

from .utils import (
    get_data_dir,
    write_file_text,
    today_str,
    load_json,
    save_json,
)
from .knowledge_base import KnowledgeBase
from .curriculum import Curriculum


class FlashcardGenerator:
    """
    Flashcard generator.
    Automatically extracts key concepts from knowledge base text, generates Q&A pairs,
    and supports exporting to Anki CSV format.
    """

    def __init__(self):
        self.flashcards_dir: Path = get_data_dir("flashcards")
        self.kb: KnowledgeBase = KnowledgeBase()
        self.manual_file: Path = self.flashcards_dir / "manual_flashcards.json"
        self.curriculum: Curriculum = Curriculum()

    # --- manual flashcards ------------------------------------------------

    def _load_manual(self) -> list[dict[str, str]]:
        """Load the manually-added flashcards."""
        data = load_json(self.manual_file)
        records = data.get("cards", [])
        return records if isinstance(records, list) else []

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
        Add a manually-created flashcard and persist it to manual_flashcards.json.

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
    ) -> tuple[str, str]:
        """
        Browse the curriculum to pick a subject and module.
        Returns (subject, module) or ("", "") if the curriculum is empty / user aborts.
        """
        subjects = self.curriculum.all_subjects(level)
        if not subjects:
            print("\n  ℹ️  Curriculum is empty — skipping subject/module selection.")
            return "", ""

        print("\n  Pick a subject (blank to skip):")
        for i, s in enumerate(subjects, 1):
            print(f"    [{i}] {s}")
        choice = self._prompt("  > ").strip()
        if not choice.isdigit():
            return "", ""
        idx = int(choice) - 1
        if idx < 0 or idx >= len(subjects):
            return "", ""
        subject = subjects[idx]

        modules = self.curriculum.all_modules(level, subject)
        if not modules:
            print(f"\n  ℹ️  No modules in {subject}.")
            return subject, ""

        print(f"\n  {subject} — pick a module (blank to skip):")
        for i, m in enumerate(modules, 1):
            print(f"    [{i}] {m}")
        choice = self._prompt("  > ").strip()
        if not choice.isdigit():
            return subject, ""
        idx = int(choice) - 1
        if idx < 0 or idx >= len(modules):
            return subject, ""
        return subject, modules[idx]

    def manual_flashcard(self, level: str = "L1") -> None:
        """
        Interactively add one or more flashcards by hand, optionally selecting
        the subject and module from the curriculum. Aborts cleanly on Ctrl+C/Ctrl+D.
        """
        try:
            print("\n" + "=" * 50)
            print("  🃏 Add Manual Flashcard")
            print("=" * 50)

            while True:
                subject, module = self._pick_subject_and_module(level)
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
                print(f"  ✅ Saved to: {filepath}\n")

            print("\n  ✅ Finished adding manual flashcards.")

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — current flashcard was NOT saved.")

    def extract_concepts(self, text: str) -> list[dict[str, str]]:
        """
        Extract key concepts from text, generating Q&A pairs.

        Recognition strategy:
        1. Look for patterns like "X is defined as/means" and related definition markers
        2. Look for bold/heading-style terms
        3. Look for formulas / key numbers

        Parameters:
            text: knowledge base page text

        Returns:
            a list of {"question": "...", "answer": "..."} dicts
        """
        concepts = []

        # Pattern 1: "X is defined as / means Y"
        pattern1 = re.compile(
            r"([\u4e00-\u9fff\w\s（）()（）]{2,40})[，,]?\s*(是指|即|定义为|指的是|意思是)\s*[：:]?\s*([\u4e00-\u9fff\w\s（）()（）,.，。；;！!？?]{3,200})",
        )
        for match in pattern1.finditer(text):
            term = match.group(1).strip()
            definition = match.group(3).strip()
            if len(term) >= 2 and len(definition) >= 5:
                concepts.append({
                    "question": f"What is {term}?",
                    "answer": definition.rstrip("。，,.") + ".",
                })

        # Pattern 2: find English abbreviations and their Chinese full forms
        pattern2 = re.compile(
            r"([A-Z]{2,8})\s*[（(]\s*([\u4e00-\u9fff\w\s]{2,40})\s*[）)]",
        )
        for match in pattern2.finditer(text):
            abbr = match.group(1).strip()
            full = match.group(2).strip()
            if len(abbr) >= 2:
                concepts.append({
                    "question": f"What is the full form of {abbr}?",
                    "answer": f"{abbr}: {full}.",
                })

        # Pattern 3: look for formulas (equations containing =)
        pattern3 = re.compile(r"([\u4e00-\u9fff\w\s（）()（）]{2,30})\s*[:：]?\s*(.+?=.+?)(?:[，,。\n]|$)")
        for match in pattern3.finditer(text):
            name = match.group(1).strip()
            formula = match.group(2).strip()
            if len(formula) >= 5 and len(formula) <= 150:
                concepts.append({
                    "question": f"What is the formula for {name}?",
                    "answer": formula.rstrip("。，,.") + ".",
                })

        # De-duplicate (based on question)
        seen = set()
        unique = []
        for c in concepts:
            if c["question"] not in seen:
                seen.add(c["question"])
                unique.append(c)

        return unique

    def generate_by_subject(self, subject: str = "") -> str:
        """
        Generate flashcards by subject.

        Parameters:
            subject: subject name (used to filter files; empty string means all)

        Returns:
            the path of the generated flashcard file
        """
        all_data = self.kb.load_all()
        all_cards = []

        for filepath, pages in all_data.items():
            fname = Path(filepath).stem

            # If a subject is specified, filter by file name
            if subject and subject.lower() not in fname.lower():
                continue

            for page_num, page_text in pages.items():
                cards = self.extract_concepts(page_text)
                for card in cards:
                    card["source"] = f"{fname} (P{page_num})"
                all_cards.extend(cards)

        if not all_cards:
            return ""

        # Determine the output file name
        if subject:
            out_name = f"{today_str()}_{subject}_flashcards.md"
        else:
            out_name = f"{today_str()}_all_flashcards.md"

        out_path = self.flashcards_dir / out_name

        # Generate Markdown-format flashcards
        lines = [f"# CFA Flashcards - {subject or 'All subjects'}\n", f"> Generated: {today_str()}\n\n"]
        for i, card in enumerate(all_cards, 1):
            lines.append(f"## Flashcard {i}\n")
            lines.append(f"**Q**: {card['question']}\n\n")
            lines.append(f"**A**: {card['answer']}\n\n")
            lines.append(f"*Source: {card.get('source', '')}*\n\n")
            lines.append("---\n\n")

        write_file_text(out_path, "".join(lines))
        return str(out_path)

    def export_anki_csv(self, subject: str = "") -> str:
        """
        Export to an Anki-compatible CSV format.

        CSV columns: Front, Back, Tags, Source

        Parameters:
            subject: subject filter

        Returns:
            the path of the generated CSV file
        """
        all_data = self.kb.load_all()
        all_cards = []

        for filepath, pages in all_data.items():
            fname = Path(filepath).stem
            if subject and subject.lower() not in fname.lower():
                continue

            for page_num, page_text in pages.items():
                cards = self.extract_concepts(page_text)
                for card in cards:
                    all_cards.append({
                        "Front": card["question"],
                        "Back": card["answer"],
                        "Tags": fname,
                        "Source": f"{fname} P{page_num}",
                    })

        if not all_cards:
            return ""

        out_name = f"{today_str()}_{subject or 'all'}_anki.csv"
        out_path = self.flashcards_dir / out_name

        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Front", "Back", "Tags", "Source"])
            writer.writeheader()
            writer.writerows(all_cards)

        return str(out_path)

    def interactive_generate(self) -> None:
        """Interactively generate flashcards"""
        print("\n" + "=" * 50)
        print("  🃏 Generate Flashcards")
        print("=" * 50)

        # Show knowledge base statistics
        stats = self.kb.get_stats()
        print(f"\nKnowledge base status: {stats['total_files']} files, {stats['total_pages']} pages")
        for f in stats["files"]:
            print(f"  - {f['name']} ({f['pages']} pages)")

        subject = input("\nEnter a subject filter (leave empty for all): ").strip()

        print("\nChoose an export format:")
        print("  [1] Markdown format")
        print("  [2] Anki CSV format")
        print("  [3] Both")
        choice = input("Choice (1/2/3): ").strip()

        if choice in ("1", "3"):
            path = self.generate_by_subject(subject)
            if path:
                print(f"✅ Markdown flashcards generated: {path}")
            else:
                print("⚠️ No matching knowledge content found")

        if choice in ("2", "3"):
            path = self.export_anki_csv(subject)
            if path:
                print(f"✅ Anki CSV generated: {path}")
            else:
                print("⚠️ No matching knowledge content found")
