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
from cfa_prep.utils import (
    get_project_root,
    get_data_root,
    get_data_dir,
    fuzzy_match,
    extract_context,
    today_str,
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
    """Test the progress tracker"""
    tracker = ProgressTracker()
    content = tracker.load()
    assert "# CFA Study Progress" in content
    print(f"  ✅ Progress tracker is fine")


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
    topics = engine._generate_l1_quiz()
    assert len(topics) <= 10
    print(f"  ✅ Quiz engine is fine (L1 question count: {len(topics)})")


def test_flashcard_generator():
    """Test the flashcard generator"""
    generator = FlashcardGenerator()
    # Test concept extraction (with mock text)
    sample_text = """
    FCFE（Free Cash Flow to Equity）是指公司可分配给股东的现金流。
    DDM 即股利折现模型，是一种股票估值方法。
    FCFF = EBIT(1-T) + Depreciation - CapEx - ΔWC
    """
    concepts = generator.extract_concepts(sample_text)
    assert len(concepts) > 0
    print(f"  ✅ Flashcard generator is fine (concepts extracted: {len(concepts)})")


def test_settings():
    """Test config read/write"""
    test_settings_data = {"level": "L1", "version": "1.0", "data_root": str(get_data_root())}
    save_settings(test_settings_data)
    settings = load_settings()
    assert settings.get("level") == "L1"
    assert settings.get("version") == "1.0"
    print(f"  ✅ Config read/write is fine (level: {settings.get('level')})")


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
            os.environ.pop("CFA_PREP_HOME", None)


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
        ("Config read/write", test_settings),
        ("Data root env override", test_data_root_env_override),
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
