"""
CFA Prep CLI - Manual flashcard module
Author: CodeBuddy AI Assistant
Purpose: Manually add Q&A flashcards, optionally selecting the subject/module
         from the curriculum, and store them at data/flashcards/flashcards.json.
"""

from pathlib import Path
from typing import TypedDict, cast

from .curriculum import Curriculum
from .images import attach_image, clean_pasted_path, image_lines, open_externally
from .input_flow import (
    BACK,
    HINT,
    QUIT,
    FinishSession,
    QuitSession,
    SkipQuestion,
    Step,
    StepFlow,
)
from .tables import Table, render_markdown_table, render_table, table_from_text
from .utils import (
    get_data_dir,
    load_json,
    save_json,
    today_str,
    write_file_text,
)


class _FlashcardOptional(TypedDict, total=False):
    """The optional part of a flashcard: its picture, the caption and its table."""
    images: list[str]        # relative to the flashcards folder
    image_caption: str
    table: Table | None      # the table the question refers to


class Flashcard(_FlashcardOptional):
    """One flashcard: the fields that every card holds are the required ones."""
    date: str
    level: str
    subject: str
    module: str
    question: str
    answer: str


class FlashcardGenerator:
    """
    Flashcard manager.
    Manages manually-added Q&A flashcards stored in a single JSON file.
    """

    def __init__(self):
        self.flashcards_dir: Path = get_data_dir("flashcards")
        self.manual_file: Path = self.flashcards_dir / "flashcards.json"
        self.images_dir: Path = self.flashcards_dir / "images"
        self.curriculum: Curriculum = Curriculum()

    # --- manual flashcards ------------------------------------------------

    def _load_manual(self) -> list[Flashcard]:
        """Load the manually-added flashcards."""
        data = load_json(self.manual_file)
        return cast(list[Flashcard], data.get("cards", []))

    def list_manual_cards(self) -> list[Flashcard]:
        """Return the manually-added flashcards, as stored."""
        return self._load_manual()

    def _save_manual(self, cards: list[Flashcard]) -> None:
        """Save the manually-added flashcards."""
        save_json(self.manual_file, {"cards": cards})

    def add_manual(
        self,
        question: str,
        answer: str,
        level: str = "L1",
        subject: str = "",
        module: str = "",
        images: list[str] | None = None,
        image_caption: str = "",
        table: Table | None = None,
    ) -> str:
        """
        Add a manually-created flashcard and persist it to flashcards.json.

        Parameters:
            question: the flashcard front (question)
            answer: the flashcard back (answer)
            level: exam level (L1/L2/L3)
            subject: subject from the curriculum (optional)
            module: module within the subject (optional)
            images: the images of the card, relative to the flashcards folder
                (for example "images/9f2c1a7b.png") (optional)
            image_caption: the caption shown under the images (optional)
            table: the table the question refers to (optional)

        Returns:
            the path of the manual flashcard file
        """
        cards = self._load_manual()
        card: Flashcard = {
            "date": today_str(),
            "level": level,
            "subject": subject,
            "module": module,
            "question": question,
            "answer": answer,
        }
        if images:
            card["images"] = images
        if image_caption:
            card["image_caption"] = image_caption
        if table:
            card["table"] = table
        cards.append(card)
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
        lines = ["# Manual CFA Flashcards\n", f"> Generated: {today_str()}\n\n"]
        for i, card in enumerate(cards, 1):
            location = " / ".join(
                part for part in (card.get("subject", ""), card.get("module", "")) if part
            )
            lines.append(f"## Flashcard {i}\n")
            lines.append(f"**Q**: {card['question']}\n\n")
            table = card.get("table")
            if table:
                markdown = render_markdown_table(table)
                if markdown:
                    lines.append(f"\n{markdown}\n\n")
            lines.append(f"**A**: {card['answer']}\n\n")
            for relative in card.get("images", []):
                caption = card.get("image_caption", "")
                lines.append(f"![{caption}]({relative})\n\n")
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

    def _attach_image(self, raw: str, caption: str) -> tuple[list[str], str]:
        """
        Copy the picture of the card into the images folder of the data root.

        The path may be pasted (Windows Terminal puts it in quotes) and the file
        is copied, so the card keeps working when the data root moves.
        """
        if not raw.strip():
            return [], ""
        source = Path(clean_pasted_path(raw)).expanduser()
        try:
            relative = attach_image(source, self.images_dir)
        except ValueError as exc:
            print(f"  ❌ {exc}")
            return [], ""
        print(f"  📷 Image attached: {relative}")
        return [relative], caption

    def _pick_subject_and_module(
        self, level: str = "L1"
    ) -> tuple[str, str] | None:
        """
        Browse the curriculum to pick a subject and module.

        `\\b` goes back to the list of subjects, `\\q` leaves the picker.
        Returns (subject, module), or None if the user finishes (blank subject),
        or ("", "") if the curriculum is empty.
        """
        subjects = self.curriculum.all_subjects(level)
        if not subjects:
            print("\n  ℹ️  Curriculum is empty — skipping subject/module selection.")
            return "", ""

        while True:
            print("\n  Pick a subject (blank to finish):")
            for i, s in enumerate(subjects, 1):
                print(f"    [{i}] {s}")
            choice = self._prompt("  > ").strip()
            if choice == QUIT:
                return None
            if choice == BACK:
                print("  ⚠️ Already at the first step.")
                continue
            if not choice.isdigit():
                return None
            idx = int(choice) - 1
            if idx < 0 or idx >= len(subjects):
                return None
            subject = subjects[idx]

            modules = self.curriculum.all_modules(level, subject)
            if not modules:
                print(
                    f"\n  ❌ No modules in {subject} — cannot add a card without a module."
                )
                return None

            while True:
                print(f"\n  {subject} — pick a module (blank to finish):")
                for i, m in enumerate(modules, 1):
                    print(f"    [{i}] {m}")
                choice = self._prompt("  > ").strip()
                if choice == QUIT:
                    return None
                if choice == BACK:
                    # Back to the list of subjects
                    print("  ⬅️ Back to: subject")
                    break
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

        Every step of a card can be reached again: `\\b` goes one step back,
        `\\r` starts the card over and `\\q` leaves the session.
        """
        added = 0
        try:
            print("\n" + "=" * 50)
            print("  🃏 Add Manual Flashcard")
            print("=" * 50)
            print(f"\n  {HINT}")

            # The table of the card that is being typed
            tables: dict[str, Table | None] = {}

            while True:
                picked = self._pick_subject_and_module(level)
                if picked is None:
                    break
                subject, module = picked
                location = " / ".join(p for p in (subject, module) if p)
                tables.clear()

                def take_table(raw: str, previous: str) -> str:
                    """Read the table of the card and show it as it will be shown."""
                    if not raw.strip():
                        if previous:
                            print("  ↩️ Keeping the table from before.")
                            return previous
                        tables["table"] = None
                        return raw
                    table = table_from_text(raw)
                    tables["table"] = table
                    if table:
                        print("\n  📊 Table:")
                        for row in render_table(table, indent="    "):
                            print(row)
                        print()
                    else:
                        print("  (ignored — a table needs at least two columns)")
                    return raw

                def check_question(value: str, previous: str) -> None:
                    """A blank question ends the session."""
                    del previous
                    if not value.strip():
                        raise FinishSession

                def check_answer(value: str, previous: str) -> None:
                    """A card without an answer is skipped."""
                    del previous
                    if not value.strip():
                        print("  ❌ Answer cannot be empty — skipping this card.")
                        raise SkipQuestion

                flow = StepFlow(self._prompt)
                steps = [
                    Step(
                        "question",
                        f"\nQuestion{(' [' + location + ']') if location else ''}"
                        + " (blank to finish): ",
                        on_value=check_question,
                    ),
                    Step("answer", "Answer: ", on_value=check_answer),
                    Step(
                        "table",
                        "  Paste the table of the card (press Enter if there is none):",
                        kind="block",
                        on_done=take_table,
                        keep_on_empty=True,
                    ),
                    Step("image", "Image path (blank for none): "),
                    Step(
                        "caption",
                        "Caption (blank for none): ",
                        # The caption is only asked for when there is a picture
                        when=lambda values: bool(values.get("image", "").strip()),
                        keep_on_empty=True,
                    ),
                ]
                try:
                    values = flow.run(steps)
                except FinishSession:
                    break
                except SkipQuestion:
                    continue
                except QuitSession:
                    print("\n  👋 Left the session.")
                    break

                # The picture is copied once the card is complete
                images, caption = self._attach_image(
                    values.get("image", ""), values.get("caption", "")
                )

                filepath = self.add_manual(
                    question=values["question"],
                    answer=values["answer"],
                    level=level,
                    subject=subject,
                    module=module,
                    images=images,
                    image_caption=caption,
                    table=tables.get("table"),
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

    def _review_keys(self, images: list[str]) -> str:
        """
        Return the keys of the review prompt that follows the answer.

        The option to open a picture only shows up when the file is really
        there - a picture that is gone cannot be opened, so it is not offered.
        """
        keys = "[Enter] next"
        if any((self.flashcards_dir / relative).is_file() for relative in images):
            keys += ", [o] open image"
        if images:
            keys += ", [s] path"
        keys += ", [b] back, [q] quit"
        return keys

    def view_flashcards(self, level: str = "L1") -> None:
        """
        Interactively review flashcards: show each question, then reveal its
        answer - with the table and the picture of the card - or skip to the
        next card. Optionally filter by subject.
        Aborts cleanly on Ctrl+C/Ctrl+D.
        """
        try:
            print("\n" + "=" * 50)
            print("  🃏 Review Flashcards")
            print("=" * 50)

            cards = self._load_manual()
            if not cards:
                print("\n  No flashcards yet. Add some with 'cfa-prep flashcard -a'.")
                return

            subject = self._pick_subject_filter(level)
            if subject:
                filtered = [c for c in cards if c.get("subject") == subject]
                if not filtered:
                    print(f"\n  No flashcards for subject: {subject}")
                    return
                cards = filtered

            total = len(cards)
            print(f"\n  {total} flashcard(s). [Enter] reveal answer, [n] next, [q] quit.\n")
            all_images = [
                relative
                for card in cards
                for relative in (card.get("images") or [])
            ]
            if any((self.flashcards_dir / relative).is_file() for relative in all_images):
                print("  The pictures of the cards are shown after the answer.\n")

            i = 0
            while i < total:
                card = cards[i]
                location = " / ".join(
                    part for part in (card.get("subject", ""), card.get("module", "")) if part
                )
                print(f"{'─' * 50}")
                print(f"  [{i + 1}/{total}] Q: {card['question']}\n")

                action = self._prompt(
                    "  [Enter] reveal answer, [n] next, [q] quit: "
                ).strip().lower()
                if action == "q":
                    break
                if action == "n":
                    i += 1
                    continue

                # The answer, and with it the table and the picture of the card
                print(f"  A: {card['answer']}")
                if location:
                    print(f"      ({location})")
                print()

                table = card.get("table")
                if table:
                    for row in render_table(table, indent="  "):
                        print(row)
                    print()

                # The picture itself is opened in the image viewer of the system
                images = list(card.get("images") or [])
                caption = card.get("image_caption", "")
                if images:
                    print(f"  📷 {len(images)} image(s) attached\n")
                    for relative in images:
                        for line in image_lines(self.flashcards_dir / relative, caption):
                            print(line)

                # The image keys keep the card on the screen, so the header is
                # not printed again after them.
                while True:
                    action = self._prompt(f"  {self._review_keys(images)}: ").strip().lower()

                    if action == "o":
                        for relative in images:
                            target = self.flashcards_dir / relative
                            if not target.is_file():
                                # The picture is gone, so there is nothing to open
                                continue
                            if open_externally(target):
                                print(f"  🖼️  Opened: {target}")
                            else:
                                print(f"  ❌ Could not open: {target}")
                        continue
                    if action == "s":
                        for relative in images:
                            print(f"  📁 {self.flashcards_dir / relative}")
                        continue
                    break

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
