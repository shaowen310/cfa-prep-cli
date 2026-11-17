"""
CFA Prep CLI - Tests for the curriculum module
Author: CodeBuddy AI Assistant
Purpose: Check the curriculum: seeding, importing and the modules the quiz draws its material from.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.curriculum import Curriculum
from cfa_prep.quiz_engine import QuizEngine


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
            print("  ✅ Curriculum seed + load is fine")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_curriculum_import_nested_modules():
    """Test that nested {module: [topics]} curriculum imports and flattens correctly"""
    import json
    import tempfile

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
    print("  ✅ Curriculum subject normalization is fine")


def test_quiz_uses_curriculum():
    """Test that the quiz engine draws its topic pool from the imported curriculum"""
    import json
    import tempfile

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
