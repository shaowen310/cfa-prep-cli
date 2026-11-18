"""
CFA Prep CLI - Tests for the search module
Author: CodeBuddy AI Assistant
Purpose: Check the unified search over the curriculum, the flashcards and the mistake log.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))




def test_search_covers_all_sources():
    """Test that the search looks into the curriculum, the flashcards and the mistake log"""
    import tempfile

    from cfa_prep.curriculum import Curriculum
    from cfa_prep.flashcard_generator import FlashcardGenerator
    from cfa_prep.mistake_analyzer import MistakeAnalyzer
    from cfa_prep.search import search_all

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            _ = Curriculum().save({
                "L1": {
                    "Economics": {
                        "Module 3: Fiscal Policy": ["The role of the arbitrageur"],
                    }
                }
            })
            _ = FlashcardGenerator().add_manual(
                question="What is an arbitrageur?",
                answer="A trader who exploits price differences between markets.",
                level="L1",
                subject="Economics",
                module="Module 3: Fiscal Policy",
            )
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question="What is a deflationary gap?",
                user_answer="An expansionary gap",
                correct_answer="A deflationary gap",
                explanation="Aggregate demand falls below potential output.",
                module_name="Module 3: Fiscal Policy",
                options=["A deflationary gap", "An expansionary gap", "A stagflation"],
            )

            outcome = search_all("arbitrageur", use_fuzzy=False)
            sources = {hit["source"] for hit in outcome["hits"]}
            assert "curriculum" in sources, outcome
            assert "flashcard" in sources, outcome
            assert outcome["curriculum_modules"] == 1, outcome
            assert outcome["curriculum_topics"] == 1, outcome
            assert outcome["flashcards"] == 1, outcome
            assert outcome["mistakes"] == 1, outcome

            # A curriculum hit carries no snippet: the title is the content
            curriculum_hits = [h for h in outcome["hits"] if h["source"] == "curriculum"]
            assert curriculum_hits, outcome
            assert curriculum_hits[0]["snippet"] == "", curriculum_hits

            outcome = search_all("deflationary", use_fuzzy=False)
            sources = {hit["source"] for hit in outcome["hits"]}
            assert "mistake" in sources, outcome

            print("  ✅ The search covers the curriculum, flashcards and mistakes")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_search_hits_keep_the_original_data():
    """Test that a hit keeps the entry it came from, so it can be shown in full"""
    import io
    import tempfile
    from contextlib import redirect_stdout

    from cfa_prep.curriculum import Curriculum
    from cfa_prep.flashcard_generator import FlashcardGenerator
    from cfa_prep.mistake_analyzer import MistakeAnalyzer
    from cfa_prep.search import print_hit_record, search_all

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            _ = Curriculum().save({
                "L1": {
                    "Economics": {
                        "Module 3: Fiscal Policy": ["The role of the arbitrageur"],
                    }
                }
            })
            _ = FlashcardGenerator().add_manual(
                question="What is an arbitrageur?",
                answer="A trader who exploits price differences between markets.",
                level="L1",
                subject="Economics",
                module="Module 3: Fiscal Policy",
            )
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question="What is a deflationary gap?",
                user_answer="An expansionary gap",
                correct_answer="A deflationary gap",
                explanation="Aggregate demand falls below potential output.",
                module_name="Module 3: Fiscal Policy",
                options=["A deflationary gap", "An expansionary gap", "A stagflation"],
            )

            # Every hit carries the entry it came from
            hits = search_all("arbitrageur", use_fuzzy=False)["hits"]
            assert hits, hits
            for hit in hits:
                record = hit.get("record")
                assert record is not None, hit
                assert record["source"] == hit["source"], hit

            # The curriculum hit keeps the topics of its module
            curriculum_hit = next(h for h in hits if h["source"] == "curriculum")
            curriculum_record = curriculum_hit.get("record")
            assert curriculum_record is not None, curriculum_hit
            assert curriculum_record.get("topics") == ["The role of the arbitrageur"], (
                curriculum_hit
            )

            # The flashcard hit keeps the answer of the card
            card_hit = next(h for h in hits if h["source"] == "flashcard")
            card_record = card_hit.get("record")
            assert card_record is not None, card_hit
            assert card_record.get("answer", "").startswith("A trader"), card_hit

            # The mistake hit keeps the mistake itself, so the browser can show it
            mistake_hits = search_all("deflationary", use_fuzzy=False)["hits"]
            mistake_hit = next(h for h in mistake_hits if h["source"] == "mistake")
            mistake_record = mistake_hit.get("record")
            assert mistake_record is not None, mistake_hit
            mistake = mistake_record.get("mistake")
            assert mistake is not None, mistake_hit
            assert mistake.get("options") == [
                "A deflationary gap",
                "An expansionary gap",
                "A stagflation",
            ], mistake
            assert mistake_record.get("module") == "Module 3: Fiscal Policy", mistake_hit

            # The entry is shown in full
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                print_hit_record(mistake_record)
            output = buffer.getvalue()
            assert "A deflationary gap" in output, output
            assert "Answer: A" in output, output
            assert "Aggregate demand falls below potential output." in output, output
            # Like the mistake browser, the old wrong answer is not shown
            assert "Your answer" not in output, output

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                print_hit_record(card_record)
            output = buffer.getvalue()
            assert "A trader who exploits price differences" in output, output

            # The module view of the mistake browser is reachable from a hit
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                MistakeAnalyzer().print_module_mistakes(
                    "Economics", "Module 3: Fiscal Policy"
                )
            output = buffer.getvalue()
            assert "1 in Economics | Module 3: Fiscal Policy" in output, output
            assert "What is a deflationary gap?" in output, output

            print("  ✅ A hit keeps the original data and shows it in full")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_search_whole_word():
    """Test that the search matches the keyword as a whole word"""
    import tempfile

    from cfa_prep.flashcard_generator import FlashcardGenerator
    from cfa_prep.search import search_all

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            _ = FlashcardGenerator().add_manual(
                question="A tariff on imports",
                answer="Corporates pay tariffs; the corporate burden matters.",
                level="L1",
                subject="Economics",
                module="Module 6: International Trade",
            )

            # "tariff" is a word of the text, "tariffs" is not
            hits = search_all("tariff", use_fuzzy=False)["hits"]
            assert len(hits) == 1, hits
            assert "tariff" in hits[0]["snippet"].lower(), hits

            # "corporate" must not be found through "rate"
            hits = search_all("rate", use_fuzzy=False)["hits"]
            assert hits == [], hits

            # The plural is a word of its own
            hits = search_all("tariffs", use_fuzzy=False)["hits"]
            assert len(hits) == 1, hits
            print("  ✅ The search matches whole words")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)
