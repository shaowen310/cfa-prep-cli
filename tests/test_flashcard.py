"""
CFA Prep CLI - Tests for the flashcard generator module
Author: CodeBuddy AI Assistant
Purpose: Check the manual flashcards: adding them and reviewing them.
"""

import contextlib
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.curriculum import Curriculum
from cfa_prep.flashcard_generator import FlashcardGenerator


def test_flashcard_generator():
    """Test manually adding a flashcard (with curriculum subject/module selection)"""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            # Populate a small curriculum so subject/module selection works
            c = Curriculum()
            src = Path(tmp) / "cur.json"
            _ = src.write_text(
                json.dumps({"L1": {"Economics": {"Module 1: Intro": ["Demand"]}}}),
                encoding="utf-8",
            )
            c.import_file(str(src))

            generator = FlashcardGenerator()
            filepath = generator.add_manual(
                question="What is demand?",
                answer="Desire backed by ability",
                level="L1",
                subject="Economics",
                module="Module 1: Intro",
            )
            assert Path(filepath).exists()
            cards = generator._load_manual()  # pyright: ignore[reportPrivateUsage]
            assert len(cards) == 1
            assert cards[0].get("question") == "What is demand?"
            assert cards[0].get("answer") == "Desire backed by ability"
            assert cards[0].get("subject") == "Economics"
            assert cards[0].get("module") == "Module 1: Intro"
            print(f"  ✅ Flashcard generator is fine (manual cards: {len(cards)})")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def _write_picture(path: Path) -> Path:
    """Write a small picture file (the CLI never reads its content)."""
    _ = path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return path


def test_flashcard_with_image():
    """Test that a card can carry an image and that the export embeds it"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            generator = FlashcardGenerator()
            _ = generator.add_manual(
                question="What is the yield curve?",
                answer="Spot rates by maturity",
                level="L1",
                subject="Fixed Income",
                module="Module 3: Yield Curve",
                images=["images/diagram.png"],
                image_caption="Spot vs forward curve",
            )

            cards = generator._load_manual()  # pyright: ignore[reportPrivateUsage]
            assert len(cards) == 1
            assert cards[0].get("images") == ["images/diagram.png"], cards[0]
            assert cards[0].get("image_caption") == "Spot vs forward curve"

            # The markdown export embeds the picture
            out = Path(generator.export_manual_markdown())
            text = out.read_text(encoding="utf-8")
            assert "![Spot vs forward curve](images/diagram.png)" in text, text
            print("  ✅ A flashcard can carry an image")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_flashcard_missing_image():
    """Test that a picture that is gone hides the option to open it"""
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            generator = FlashcardGenerator()
            # The picture is not copied into the data root, so it is not there
            _ = generator.add_manual(
                question="What is the yield curve?",
                answer="Spot rates by maturity",
                level="L1",
                subject="Fixed Income",
                module="Module 3: Yield Curve",
                images=["images/gone.png"],
                image_caption="Spot vs forward curve",
            )

            old_stdin = sys.stdin
            try:
                sys.stdin = io.StringIO("q\n")  # quit the review
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    generator.view_flashcards("L1")
            finally:
                sys.stdin = old_stdin

            output = buffer.getvalue()
            # The option to open a picture that is not there is not offered
            assert "[o] open image" not in output, output
            assert "not found" in output, output
            # The path of the picture is still shown
            assert "gone.png" in output, output
            print("  ✅ A missing picture hides the option to open it")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_flashcard_image_prompt():
    """Test attaching an image through the interactive prompt"""
    import io
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            source = _write_picture(Path(tmp) / "diagram.png")

            # A small curriculum, so the subject and module can be picked
            c = Curriculum()
            cur = Path(tmp) / "cur.json"
            _ = cur.write_text(
                json.dumps({"L1": {"Economics": {"Module 1: Intro": ["Demand"]}}}),
                encoding="utf-8",
            )
            c.import_file(str(cur))

            generator = FlashcardGenerator()
            old_stdin = sys.stdin
            try:
                # subject, module, question, answer, image path, caption, end
                answers = [
                    "1",
                    "1",
                    "What is demand?",
                    "Desire backed by ability",
                    f'"{source}"',
                    "A demand curve",
                    "",
                ]
                sys.stdin = io.StringIO("\n".join(answers) + "\n")
                generator.manual_flashcard("L1")
            finally:
                sys.stdin = old_stdin

            cards = generator._load_manual()  # pyright: ignore[reportPrivateUsage]
            assert len(cards) == 1, cards
            images = cards[0].get("images") or []
            assert len(images) == 1, cards[0]
            assert images[0].startswith("images/"), images[0]
            assert cards[0].get("image_caption") == "A demand curve"

            # The picture was copied into the data root
            copied = generator.flashcards_dir / images[0]
            assert copied.is_file(), copied
            assert copied.read_bytes() == source.read_bytes()
            print("  ✅ An image is attached through the prompt")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_flashcard_review():
    """Test reviewing flashcards (view question, reveal answer, skip)"""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            # Populate a small curriculum
            c = Curriculum()
            src = Path(tmp) / "cur.json"
            _ = src.write_text(
                json.dumps({"L1": {"Economics": {"Module 1: Intro": ["Demand"]}}}),
                encoding="utf-8",
            )
            c.import_file(str(src))

            generator = FlashcardGenerator()
            _ = generator.add_manual("Q1?", "A1", "L1", "Economics", "Module 1: Intro")
            _ = generator.add_manual("Q2?", "A2", "L1", "Economics", "Module 1: Intro")

            # Subject filter returns only matching cards
            cards = generator._load_manual()  # pyright: ignore[reportPrivateUsage]
            assert len(cards) == 2
            economics = [c for c in cards if c.get("subject") == "Economics"]
            assert len(economics) == 2

            # Review loop: reveal first answer, then quit
            import io
            import sys
            old_stdin = sys.stdin
            try:
                sys.stdin = io.StringIO("\n\nq\n")  # reveal, next, quit
                generator.view_flashcards("L1")
            finally:
                sys.stdin = old_stdin
            print(f"  ✅ Flashcard review is fine ({len(economics)} Economics cards)")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)
