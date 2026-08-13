# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Basic tests
Author: CodeBuddy AI Assistant
Purpose: Run basic functional tests on the core modules to ensure each module can be initialized and run correctly.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.knowledge_base import KnowledgeBase
from cfa_prep.mistake_analyzer import MistakeAnalyzer
from cfa_prep.progress_tracker import ProgressTracker
from cfa_prep.flashcard_generator import FlashcardGenerator
from cfa_prep.ips_builder import IPSBuilder
from cfa_prep.quiz_engine import QuizEngine
from cfa_prep.curriculum import Curriculum
from cfa_prep.utils import (
    get_project_root,
    get_data_root,
    get_data_dir,
    fuzzy_match,
    extract_context,
    today_iso,
    load_settings,
    save_settings,
)


def test_project_root():
    """Test whether the project root directory is correct"""
    root = get_project_root()
    assert root.exists(), "Project root directory does not exist"
    assert (root / "cfa_prep").exists(), "cfa_prep directory does not exist"
    print(f"  ✅ Project root: {root}")


def test_data_dirs():
    """Test data directory creation"""
    dirs = ["kb", "mistakes", "progress", "flashcards", "templates"]
    for d in dirs:
        p = get_data_dir(d)
        assert p.exists(), f"{d} directory creation failed"
    print(f"  ✅ All data directories are fine")


def test_fuzzy_match():
    """Test fuzzy matching"""
    assert fuzzy_match("FCFE", "Free Cash Flow to Equity") == True
    assert fuzzy_match("xyz", "Free Cash Flow to Equity") == False
    assert fuzzy_match("fcfe", "FCFE") == True
    print(f"  ✅ Fuzzy matching is fine")


def test_extract_context():
    """Test context extraction"""
    text = "The Free Cash Flow to Equity (FCFE) model values a company based on cash available to shareholders."
    snippet = extract_context(text, "FCFE")
    assert "FCFE" in snippet
    print(f"  ✅ Context extraction is fine")


def test_knowledge_base():
    """Test knowledge base initialization"""
    kb = KnowledgeBase()
    stats = kb.get_stats()
    assert "total_files" in stats
    assert "total_pages" in stats
    print(f"  ✅ Knowledge base module is fine (files: {stats['total_files']})")


def test_mistake_analyzer():
    """Test the mistake analyzer"""
    analyzer = MistakeAnalyzer()
    stats = analyzer.get_mistake_stats()
    assert "total" in stats
    print(f"  ✅ Mistake analyzer is fine (mistakes: {stats['total']})")


def test_progress_tracker():
    """Test the progress tracker stores and retrieves JSON data"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            tracker = ProgressTracker()
            # Fresh load returns default structure
            data = tracker.load()
            assert "mastered" in data
            assert "fuzzy" in data
            assert data["mastered"] == []
            assert data["fuzzy"] == []
            # Update with entries
            tracker.update(mastered=["[Econ > Module 1] Topic A"], fuzzy=["[Econ > Module 2] Topic B"])
            loaded = tracker.load()
            assert loaded["mastered"] == ["[Econ > Module 1] Topic A"]
            assert loaded["fuzzy"] == ["[Econ > Module 2] Topic B"]
            # Deduplication
            tracker.update(mastered=["[Econ > Module 1] Topic A"])
            assert len(tracker.load()["mastered"]) == 1
            # Remove entries
            _ = tracker.remove_entries({0, 1})
            assert tracker.load()["mastered"] == []
            assert tracker.load()["fuzzy"] == []
            # get_key_points_to_review returns fuzzy only
            tracker.update(fuzzy=["[Econ > Module 2] Topic B"])
            assert tracker.get_key_points_to_review() == ["[Econ > Module 2] Topic B"]
            print(f"  ✅ Progress tracker is fine")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_ips_builder():
    """Test the IPS builder"""
    builder = IPSBuilder()
    today = today_iso()
    # Test personal IPS generation
    path = builder.generate("personal", today)
    assert Path(path).exists()
    content = open(path, "r", encoding="utf-8").read()
    assert "Individual Investment Policy Statement" in content
    print(f"  ✅ IPS builder is fine (personal)")

    # Test institutional IPS generation
    path = builder.generate("institutional", today)
    assert Path(path).exists()
    content = open(path, "r", encoding="utf-8").read()
    assert "Institutional Investment Policy Statement" in content
    print(f"  ✅ IPS builder is fine (institutional)")


def test_quiz_engine():
    """Test the quiz engine"""
    engine = QuizEngine()
    topics = engine._generate_l1_quiz()  # pyright: ignore[reportPrivateUsage]
    assert len(topics) <= 10
    print(f"  ✅ Quiz engine is fine (L1 question count: {len(topics)})")


def test_flashcard_generator():
    """Test manually adding a flashcard (with curriculum subject/module selection)"""
    import tempfile
    import json

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
    import tempfile
    import json

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


def test_settings():
    """Test config read/write"""
    test_settings_data = {"level": "L1", "version": "1.0", "data_root": str(get_data_root())}
    save_settings(test_settings_data)
    settings = load_settings()
    assert settings.get("level") == "L1"
    assert settings.get("version") == "1.0"
    print(f"  ✅ Config read/write is fine (level: {settings.get('level')})")


def test_curriculum_seed_and_load():
    """Test that the curriculum loads empty when no file exists, and seed() is idempotent"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            c = Curriculum()
            # No file yet: load() returns an empty curriculum (no bundled scaffold)
            assert c.load() == {}
            assert c.all_subjects("L1") == []
            assert c.all_topics("L1") == []

            # seed() creates an empty file; a second seed() is idempotent
            assert c.seed() is True, "First seed should write a new file"
            assert c.path.exists(), "seed() should create curriculum.json"
            assert c.seed() is False, "Second seed should be a no-op"
            print(f"  ✅ Curriculum seed + load is fine")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_curriculum_import_nested_modules():
    """Test that nested {module: [topics]} curriculum imports and flattens correctly"""
    import tempfile
    import json

    nested = {
        "L1": {
            "Economics": {
                "Module 1: Intro": ["1.01 A", "1.02 B"],
                "Module 2: Policy": ["2.01 C"],
            }
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            src = Path(tmp) / "nested.json"
            _ = src.write_text(json.dumps(nested), encoding="utf-8")
            c = Curriculum()
            c.import_file(str(src))
            # Modules are preserved as the internal grouping; topics carry module labels
            topics = c.all_topics("L1")
            assert "[Economics > Module 1: Intro] 1.01 A" in topics
            assert "[Economics > Module 1: Intro] 1.02 B" in topics
            assert "[Economics > Module 2: Policy] 2.01 C" in topics
            # Module names are queryable per subject
            assert c.all_modules("L1", "Economics") == ["Module 1: Intro", "Module 2: Policy"]
            # resolve_label: fuzzy match on topic portion
            resolved = c.resolve_label("1.01 A", "L1")
            assert resolved is not None
            assert "1.01 A" in resolved
            # resolve_label: exact full-label match
            assert c.resolve_label("[Economics > Module 1: Intro] 1.01 A", "L1") is not None
            # resolve_subject: alias
            assert c.resolve_subject("econ", "L1") == "Economics"
            # resolve_module: exact match expands all topics
            module_topics = c.resolve_module("Module 1: Intro", "L1")
            assert len(module_topics) == 2
            assert "[Economics > Module 1: Intro] 1.01 A" in module_topics
            assert "[Economics > Module 1: Intro] 1.02 B" in module_topics
            # resolve_module: fuzzy match
            fuzzy_module = c.resolve_module("Module 2", "L1")
            assert len(fuzzy_module) == 1
            assert "[Economics > Module 2: Policy] 2.01 C" in fuzzy_module
            # resolve_module: no match returns empty
            assert c.resolve_module("Nonexistent Module", "L1") == []
            print(f"  ✅ Curriculum nested-module import is fine ({len(topics)} topics)")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_curriculum_normalize_subject():
    """Test subject auto-correction (aliases + case + whitespace)"""
    c = Curriculum()
    # alias correction: FRA -> Financial Statement Analysis
    assert c.normalize_subject("FRA") == "Financial Statement Analysis"
    assert c.normalize_subject("fra") == "Financial Statement Analysis"
    assert c.normalize_subject("financial reporting") == "Financial Statement Analysis"
    # canonical exact match
    assert c.normalize_subject("Ethics") == "Ethical & Professional Standards"
    assert c.normalize_subject("quant") == "Quantitative Methods"
    # unknown returns None
    assert c.normalize_subject("Zzznonsense") is None
    print(f"  ✅ Curriculum subject normalization is fine")


def test_quiz_uses_curriculum():
    """Test that the quiz engine draws its topic pool from the imported curriculum"""
    import tempfile
    import json

    data = {"L1": {"Economics": ["Demand and supply", "Monetary policy"]}}
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            c = Curriculum()
            _ = c.seed()
            src = Path(tmp) / "cur.json"
            _ = src.write_text(json.dumps(data), encoding="utf-8")
            c.import_file(str(src))
            engine = QuizEngine()
            topics = engine._get_all_topics("L1")  # pyright: ignore[reportPrivateUsage]
            assert len(topics) > 0
            # Flat imports get wrapped under the default module "General"
            assert "[Economics > General] Demand and supply" in topics, \
                "L1 topics should come from the imported curriculum"
            print(f"  ✅ Quiz engine uses curriculum ({len(topics)} L1 topics)")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_data_root_env_override():
    """Test that get_data_root() honors the CFA_PREP_HOME env var"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            root = get_data_root()
            assert root == Path(tmp), f"Expected {tmp}, got {root}"
            assert root.exists(), "data root directory was not created"
            print(f"  ✅ Data root honors CFA_PREP_HOME: {root}")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  🧪 CFA Prep CLI - Basic Tests")
    print("=" * 60 + "\n")

    tests = [
        ("Project root", test_project_root),
        ("Data directories", test_data_dirs),
        ("Fuzzy matching", test_fuzzy_match),
        ("Context extraction", test_extract_context),
        ("Knowledge base", test_knowledge_base),
        ("Mistake analyzer", test_mistake_analyzer),
        ("Progress tracker", test_progress_tracker),
        ("IPS builder", test_ips_builder),
        ("Quiz engine", test_quiz_engine),
        ("Flashcard generator", test_flashcard_generator),
        ("Flashcard review", test_flashcard_review),
        ("Config read/write", test_settings),
        ("Data root env override", test_data_root_env_override),
        ("Curriculum seed/load", test_curriculum_seed_and_load),
        ("Curriculum nested-module import", test_curriculum_import_nested_modules),
        ("Curriculum subject normalization", test_curriculum_normalize_subject),
        ("Quiz uses curriculum", test_quiz_uses_curriculum),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Test results: {passed} passed / {failed} failed / {len(tests)} total")
    print(f"{'=' * 60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
