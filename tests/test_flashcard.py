"""
CFA Prep CLI - Tests for the flashcard generator module
Author: CodeBuddy AI Assistant
Purpose: Check the manual flashcards: adding them and reviewing them.
"""

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
            assert cards[0]["question"] == "What is demand?"
            assert cards[0]["answer"] == "Desire backed by ability"
            assert cards[0]["subject"] == "Economics"
            assert cards[0]["module"] == "Module 1: Intro"
            print(f"  ✅ Flashcard generator is fine (manual cards: {len(cards)})")
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
