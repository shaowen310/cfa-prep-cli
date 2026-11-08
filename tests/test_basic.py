"""
CFA Prep CLI - Basic tests
Author: CodeBuddy AI Assistant
Purpose: Run basic functional tests on the core modules to ensure each module can be initialized and run correctly.
"""

import math
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.baii_calculator import (
    BAIIPlus,
    _eval_expr,  # pyright: ignore[reportPrivateUsage]
)
from cfa_prep.curriculum import Curriculum
from cfa_prep.flashcard_generator import FlashcardGenerator
from cfa_prep.ips_builder import IPSBuilder
from cfa_prep.knowledge_base import KnowledgeBase
from cfa_prep.mistake_analyzer import MistakeAnalyzer
from cfa_prep.progress_tracker import ProgressTracker
from cfa_prep.quiz_engine import QuizEngine
from cfa_prep.utils import (
    extract_context,
    fuzzy_match,
    get_data_dir,
    get_data_root,
    get_project_root,
    load_home_env,
    load_settings,
    save_settings,
    set_home_env,
    set_setting,
    today_iso,
    write_file_text,
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
    print("  ✅ All data directories are fine")


def test_fuzzy_match():
    """Test fuzzy matching"""
    assert fuzzy_match("FCFE", "Free Cash Flow to Equity") == True
    assert fuzzy_match("xyz", "Free Cash Flow to Equity") == False
    assert fuzzy_match("fcfe", "FCFE") == True
    print("  ✅ Fuzzy matching is fine")


def test_extract_context():
    """Test context extraction"""
    text = "The Free Cash Flow to Equity (FCFE) model values a company based on cash available to shareholders."
    snippet = extract_context(text, "FCFE")
    assert "FCFE" in snippet
    print("  ✅ Context extraction is fine")


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
            print("  ✅ Progress tracker is fine")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_ips_builder():
    """Test the IPS builder"""
    builder = IPSBuilder()
    today = today_iso()
    # Test personal IPS generation
    path = builder.generate("personal", today)
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")
    assert "Individual Investment Policy Statement" in content
    print("  ✅ IPS builder is fine (personal)")

    # Test institutional IPS generation
    path = builder.generate("institutional", today)
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")
    assert "Institutional Investment Policy Statement" in content
    print("  ✅ IPS builder is fine (institutional)")


def test_quiz_engine():
    """Test the quiz engine"""
    engine = QuizEngine()
    topics = engine._generate_l1_quiz()  # pyright: ignore[reportPrivateUsage]
    assert len(topics) <= 10
    print(f"  ✅ Quiz engine is fine (L1 question count: {len(topics)})")


def test_baii_calculator():
    """Test the BA II Plus calculator emulator's TVM, NPV/IRR, and stats."""
    calc = BAIIPlus()

    # TVM: FV of 1000 at 5% for 10 years (compounded annually).
    # BA II Plus sign convention: an inflow today (+PV) implies an outflow later (-FV).
    calc.n, calc.iy, calc.pv, calc.pmt, calc.fv = 10, 5, 1000, 0, 0
    fv = calc.compute_tvm("FV")
    assert abs(fv + 1000 * 1.05**10) < 0.01, f"FV mismatch: {fv}"

    # Solve PV back: FV is now negative, so PV returns to +1000
    calc.fv = fv
    pv = calc.compute_tvm("PV")
    assert abs(pv - 1000) < 0.01, f"PV mismatch: {pv}"

    # PMT of an annuity: PV=1000, N=5, I/Y=10 -> PMT (negative cash outflow)
    calc.n, calc.iy, calc.pv, calc.fv = 5, 10, 1000, 0
    pmt = calc.compute_tvm("PMT")
    expected_pmt = 1000 * 0.10 / (1 - 1.10**-5)
    assert abs(pmt + expected_pmt) < 0.01, f"PMT mismatch: {pmt}"

    # Solve I/Y from the annuity values
    calc.n, calc.pv, calc.pmt, calc.fv = 5, 1000, -expected_pmt, 0
    iy = calc.compute_tvm("IY")
    assert abs(iy - 10) < 0.01, f"IY mismatch: {iy}"

    # NPV / IRR: invest 1000, receive 300 x4
    calc.clear_cashflows()
    for amt in (-1000, 300, 300, 300, 300):
        calc.add_cashflow(amt)
    npv = calc.npv(10)
    assert npv < 0, "NPV at 10% should be negative for this cash-flow series"
    irr = calc.irr()
    assert abs(irr - 7.71) < 0.1, f"IRR mismatch: {irr}"

    # One-variable stats
    calc.clear_data()
    for x in (1, 2, 3, 4, 5):
        calc.add_data(x)
    s = calc.one_var_stats()
    assert abs(s["mean"] - 3.0) < 1e-9
    # BA II Plus reports Sx as the sample standard deviation (n-1 denominator).
    assert abs(s["s_x"] - math.sqrt(2.5)) < 1e-9, f"Sx mismatch: {s['s_x']}"

    # Two-variable regression slope for y = 2x + 1
    calc.clear_data()
    for x in (1, 2, 3):
        calc.add_data(x, 2 * x + 1)
    s2 = calc.two_var_stats()
    assert abs(s2["slope"] - 2.0) < 1e-9
    assert abs(s2["intercept"] - 1.0) < 1e-9
    assert abs(s2["correlation"] - 1.0) < 1e-9

    # Percent change
    assert abs(calc.percent_change(50, 75) - 50.0) < 1e-9

    # Raw arithmetic expressions
    assert abs(_eval_expr("1+2") - 3) < 1e-9
    assert abs(_eval_expr("10*5") - 50) < 1e-9
    assert abs(_eval_expr("2^10") - 1024) < 1e-9
    assert abs(_eval_expr("3*(4-1)^2") - 27) < 1e-9
    assert abs(_eval_expr("100/3") - 100 / 3) < 1e-9
    assert abs(_eval_expr("-5+2") - (-3)) < 1e-9
    print("  ✅ BA II Plus calculator is fine")


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


def test_settings():
    """Test config read/write (level is set via set_setting, not data_root)"""
    test_settings_data: dict[str, object] = {
        "level": "L1", "version": "1.0"
    }
    save_settings(test_settings_data)
    settings = load_settings()
    assert settings.get("level") == "L1"
    assert settings.get("version") == "1.0"
    assert "data_root" not in settings, "data_root must not be stored in settings.json"

    # set_setting round-trip
    set_setting("level", "L2")
    assert load_settings().get("level") == "L2"
    set_setting("level", "L1")  # restore
    print("  ✅ Config read/write is fine (level set via set_setting)")


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


def test_quiz_no_answer_is_skipped():
    """Test that a question without an answer is recorded as skipped, never as wrong"""
    import json
    import tempfile

    from cfa_prep.mistake_analyzer import MistakeAnalyzer
    from cfa_prep.quiz_stats import RESULT_SKIPPED, RESULT_WRONG

    data = {
        "L1": {"Economics": ["Demand and supply", "Monetary policy"]},
        "L2": {"Economics": ["Inflation", "Monetary policy"]},
    }
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        import cfa_prep.quiz_engine as qe

        # The input is patched before the try block, so the original is always
        # bound: the finally block can then restore it without masking the
        # error that caused the test to fail.
        original_read_input = qe.read_input
        qe.read_input = lambda prompt="": ""

        try:
            c = Curriculum()
            _ = c.seed()
            src = Path(tmp) / "cur.json"
            _ = src.write_text(json.dumps(data), encoding="utf-8")
            c.import_file(str(src))

            # 1. The self-assessment prompt: no answer means skipped, not wrong
            engine = QuizEngine()
            outcome = engine._ask_outcome()  # pyright: ignore[reportPrivateUsage]
            assert outcome == RESULT_SKIPPED, "an empty self-assessment must be skipped"
            assert outcome != RESULT_WRONG, "an empty self-assessment must never be wrong"

            # 2. The L1 flow: a question without an answer is skipped
            engine = QuizEngine()
            engine._do_l1_quiz("L1")  # pyright: ignore[reportPrivateUsage]
            assert engine.wrong == 0, "an unanswered question must not be wrong"
            assert engine.skipped == 2, "both unanswered questions must be skipped"
            assert engine.total == 2
            for stat in engine.stats.load()["questions"].values():
                assert stat["last_result"] == RESULT_SKIPPED
                assert stat["times_wrong"] == 0
                assert stat["times_skipped"] == 1

            # 3. The L2 flow: a question without an answer is skipped
            engine = QuizEngine()
            engine._do_l2_quiz("L2")  # pyright: ignore[reportPrivateUsage]
            assert engine.wrong == 0, "an unanswered question must not be wrong"
            assert engine.skipped == 3, "all three sub-questions must be skipped"
            assert engine.total == 3
            for stat in engine.stats.load()["questions"].values():
                assert stat["last_result"] == RESULT_SKIPPED
                assert stat["times_wrong"] == 0

            # 4. The mistake replay: no answer is skipped, not wrong
            analyzer = MistakeAnalyzer()
            options = ["A tariff", "An import quota", "A voluntary export restraint"]
            _ = analyzer.add_mistake(
                subject="Economics",
                question="Which trade restriction costs the importing country most?",
                user_answer=options[0],
                correct_answer=options[1],
                key_point="Trade restrictions",
                correct_conclusion="",
                module_name="Module 6: International Trade",
                options=options,
            )
            engine = QuizEngine()
            items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
            assert len(items) == 1
            _ = engine._run_mistake_mcq(items[0])  # pyright: ignore[reportPrivateUsage]
            assert engine.wrong == 0, "an unanswered mistake must not be wrong"
            assert engine.skipped == 1, "the unanswered mistake must be skipped"
            stat = engine.stats.load()["questions"][items[0]["question_id"]]
            assert stat["last_result"] == RESULT_SKIPPED
            assert stat["times_wrong"] == 0
            assert stat["times_skipped"] == 1

            print("  ✅ Unanswered questions are recorded as skipped, not wrong")
        finally:
            qe.read_input = original_read_input
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_quiz_stats_scheduling_and_selection():
    """Test the quiz statistics: scheduling, mastery discount and priority selection"""
    import tempfile
    from datetime import date, timedelta

    from cfa_prep.quiz_engine import curriculum_question_id
    from cfa_prep.quiz_stats import (
        RESULT_CORRECT,
        RESULT_SKIPPED,
        RESULT_WRONG,
        QuizStats,
        next_due_of,
    )

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            stats = QuizStats()
            today = date(2026, 1, 1)
            wrong_topic = "[Economics > General] Discounted Dividend Valuation"
            good_topic = "[Economics > General] Monetary policy"
            unseen_topic = "[Economics > General] Inflation"

            # A wrong answer keeps the question due immediately
            wrong_id = curriculum_question_id(wrong_topic)
            stats.record_question(wrong_id, RESULT_WRONG, question=wrong_topic, today=today)
            data = stats.load()
            stat = data["questions"][wrong_id]
            assert stat["times_wrong"] == 1
            assert stat["streak"] == 0
            assert stat["interval_days"] == 0
            assert next_due_of(stat) == today, "a wrong answer must be due again now"
            assert "next_due" not in stat, "the due date must be derived, not stored"
            assert "topic" not in stat, "the topic is not stored with the question"

            # A correct answer pushes the question into the future
            good_id = curriculum_question_id(good_topic)
            stats.record_question(good_id, RESULT_CORRECT, question=good_topic, today=today)
            stat = stats.load()["questions"][good_id]
            assert stat["times_correct"] == 1
            assert stat["streak"] == 1
            assert stat["interval_days"] == 1
            assert next_due_of(stat) == today + timedelta(days=1)

            # Consecutive correct answers lengthen the interval (spaced repetition)
            for day_offset in range(1, 4):
                stats.record_question(
                    good_id,
                    RESULT_CORRECT,
                    question=good_topic,
                    today=today + timedelta(days=day_offset),
                )
            stat = stats.load()["questions"][good_id]
            assert stat["streak"] == 4
            assert stat["interval_days"] == 14, "the interval ladder should reach 14 days"

            # Priority: the wrong question outranks the mastered one; unseen ones rank high
            p_wrong = stats.priority_of(wrong_id, today=today)
            p_good = stats.priority_of(good_id, today=today)
            p_unseen = stats.priority_of(curriculum_question_id(unseen_topic), today=today)
            assert p_wrong > p_good, "repeatedly wrong questions must have a higher priority"
            assert p_unseen > p_wrong, "never tested questions must have a high priority"
            assert p_good < 0, "a mastered question must be pushed back by the mastery discount"

            # Selection must favour the weak questions over the mastered one
            candidates = [wrong_topic, good_topic, unseen_topic]
            import random as _random
            _random.seed(42)
            scored = [
                (stats.priority_of(curriculum_question_id(t), today=today), t)
                for t in candidates
            ]
            selected = stats.select_scored(scored, 2)
            assert len(selected) == 2
            assert unseen_topic in selected, "unseen questions should be selected first"
            assert wrong_topic in selected, "repeatedly wrong questions should be selected"
            assert good_topic not in selected, "a mastered question should be pushed back"

            # A skipped question was never really tested, so it must stay due
            skipped_topic = "[Economics > General] Yield curve"
            skipped_id = curriculum_question_id(skipped_topic)
            stats.record_question(
                skipped_id, RESULT_SKIPPED, question=skipped_topic, today=today
            )
            stat = stats.load()["questions"][skipped_id]
            assert stat["interval_days"] == 0, "a skipped question must be due again immediately"
            assert stats.priority_of(skipped_id, today=today) > 0, (
                "a skipped question must keep some priority"
            )

            print("  ✅ Quiz stats scheduling and priority selection work")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_question_identity():
    """Test the hashed question identity: stable, short and free of collisions"""
    import tempfile
    from datetime import date

    from cfa_prep.mistake_analyzer import question_id
    from cfa_prep.quiz_engine import curriculum_question_id
    from cfa_prep.quiz_stats import (
        RESULT_CORRECT,
        RESULT_WRONG,
        QuizStats,
    )

    stem = "Which of the following best describes a callable bond?"
    options = ["Redeemable before maturity", "Issued by a corporation", "Exchangeable for stock"]

    # The same question always gets the same id
    assert question_id(stem, options) == question_id(stem, list(options))
    # Cosmetic changes do not change the identity
    assert question_id(stem.upper(), options) == question_id(stem, options)
    # The order of the options does not change the identity
    assert question_id(stem, list(reversed(options))) == question_id(stem, options)
    # A different option set is a different question
    assert question_id(stem, options + ["Another option"]) != question_id(stem, options)
    # The id is short and does not leak the question text
    qid = question_id(stem, options)
    assert len(qid) == 18, f"unexpected id length: {qid}"
    assert stem not in qid
    # A curriculum question has its own identity, derived from its label
    curriculum_id = curriculum_question_id("[Economics > General] Inflation")
    assert curriculum_id != qid
    # The book reference tells two questions of the same topic apart
    assert curriculum_id != curriculum_question_id("[Economics > General] Inflation", "Q12")

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            stats = QuizStats()
            today = date(2026, 1, 1)
            stats.record_question(
                qid, RESULT_WRONG, question=stem, level="L1",
                source="mistake", today=today,
            )
            # The same question asked again updates the same entry
            stats.record_question(
                qid, RESULT_CORRECT, question=stem, level="L1",
                source="mistake", today=today,
            )
            questions = stats.load()["questions"]
            assert len(questions) == 1, "the same question must not create a second entry"
            stat = questions[qid]
            assert stat["times_seen"] == 2
            assert stat["times_wrong"] == 1
            assert stat["times_correct"] == 1
            assert stat["question"] == stem
            assert "topic" not in stat, "the topic is not stored with the question"

            print("  ✅ Quiz stats question identity works")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_mistake_question_id():
    """Test that a mistake stores its question id and that the quiz engine reuses it"""
    import json
    import tempfile

    from cfa_prep.mistake_analyzer import MistakeAnalyzer, question_id
    from cfa_prep.quiz_stats import QuizStats

    question = "Which trade restriction is likely to result in the greatest welfare loss?"
    options = ["A tariff", "An import quota", "A voluntary export restraint"]

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question=question,
                user_answer=options[0],
                correct_answer=options[1],
                key_point="Trade restrictions",
                correct_conclusion="",
                options=options,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert len(records) == 1
            stored = records[0].get("question_id", "")
            assert stored.startswith("q:"), "the record must carry a question id"
            assert stored == question_id(question, options), (
                "the id must be derived from the question text and its options"
            )

            # A re-logged copy keeps the id of the original question
            _ = analyzer.add_mistake(
                subject="Economics",
                question=question,
                user_answer=options[0],
                correct_answer=options[1],
                key_point="Trade restrictions",
                correct_conclusion="",
                options=options,
                existing_question_id=stored,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert records[1]["question_id"] == stored, (
                "a re-logged mistake must keep the id of the original question"
            )

            # The engine takes the id from the log, it does not derive it again
            custom_id = "q:0123456789abcdef"
            records[0]["question_id"] = custom_id
            _ = analyzer.data_file.write_text(
                json.dumps({"records": [records[0]]}, ensure_ascii=False), encoding="utf-8"
            )

            import cfa_prep.quiz_engine as qe

            original_read_input = qe.read_input
            qe.read_input = lambda prompt="": "A"
            try:
                engine = QuizEngine()
                items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
                assert len(items) == 1
                assert items[0]["question_id"] == custom_id, (
                    "the engine must read the id from mistakes.json"
                )
                _ = engine._run_mistake_mcq(items[0])  # pyright: ignore[reportPrivateUsage]
            finally:
                qe.read_input = original_read_input

            questions = QuizStats().load()["questions"]
            assert custom_id in questions, (
                "the quiz statistics must be keyed by the id stored in mistakes.json"
            )

            print("  ✅ Mistake question id is stored and reused")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_quiz_stats_file_split():
    """Test that questions and sessions live in separate files."""
    import json
    import tempfile
    from datetime import date

    from cfa_prep.quiz_stats import RESULT_CORRECT, QuizStats

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            stats = QuizStats()
            today = date(2026, 1, 1)
            stats.record_question(
                "q:test_topic_x",
                RESULT_CORRECT,
                question="[Economics > General] Topic X",
                today=today,
            )
            stats.record_session("L1", total=10, correct=7, wrong=2, skipped=1)

            # The two files are separate
            assert stats.stats_file.exists(), "the questions file must exist"
            assert stats.sessions_file.exists(), "the sessions file must exist"
            assert stats.stats_file != stats.sessions_file

            questions_raw = json.loads(stats.stats_file.read_text(encoding="utf-8"))
            sessions_raw = json.loads(stats.sessions_file.read_text(encoding="utf-8"))
            assert "questions" in questions_raw, "the questions file holds the per-question stats"
            assert "sessions" not in questions_raw, "sessions must not live in the questions file"
            assert "sessions" in sessions_raw, "the sessions file holds the history"
            assert "questions" not in sessions_raw, "questions must not live in the sessions file"

            # The aggregate report still reads the session history
            overall = stats.overall()
            assert overall["sessions"] == 1
            assert overall["total"] == 10
            assert overall["correct"] == 7

            # Reset clears both files
            stats.reset()
            assert stats.overall()["sessions"] == 0
            assert stats.load()["questions"] == {}

            print("  ✅ Quiz stats file split works")
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


def test_config_home_set():
    """Test that config home --set (set_home_env) persists and resolves via home.env.
    home.env always lives in the fixed ~/.cfa-prep/config directory, independent of the
    currently-resolved data root."""
    import tempfile

    home_env_file = Path.home() / ".cfa-prep" / "config" / "home.env"
    previous = home_env_file.read_text(encoding="utf-8") if home_env_file.exists() else None
    _ = os.environ.pop("CFA_PREP_HOME", None)
    try:
        with tempfile.TemporaryDirectory() as base:
            home_dir = Path(base) / "mydata"
            _ = home_dir.mkdir()
            _ = set_home_env(home_dir)
            assert home_env_file.exists(), "home.env should be written under ~/.cfa-prep/config"

            # Without an env var, load_home_env should pick up home.env
            load_home_env()
            assert os.environ.get("CFA_PREP_HOME") == str(home_dir), (
                f"Expected {home_dir}, got {os.environ.get('CFA_PREP_HOME')}"
            )
            assert get_data_root() == home_dir, "data root should resolve to home.env value"

            # Env var must take precedence over home.env
            other = Path(base) / "other"
            _ = other.mkdir()
            os.environ["CFA_PREP_HOME"] = str(other)
            load_home_env()
            assert get_data_root() == other, "CFA_PREP_HOME env must take precedence over home.env"
            print(f"  ✅ config home --set persists via home.env: {home_dir}")
    finally:
        _ = os.environ.pop("CFA_PREP_HOME", None)
        if previous is not None:
            _ = write_file_text(home_env_file, previous)
        elif home_env_file.exists():
            home_env_file.unlink()


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
        ("BA II Plus calculator", test_baii_calculator),
        ("Flashcard generator", test_flashcard_generator),
        ("Flashcard review", test_flashcard_review),
        ("Config read/write", test_settings),
        ("Data root env override", test_data_root_env_override),
        ("Config home set", test_config_home_set),
        ("Curriculum seed/load", test_curriculum_seed_and_load),
        ("Curriculum nested-module import", test_curriculum_import_nested_modules),
        ("Curriculum subject normalization", test_curriculum_normalize_subject),
        ("Quiz uses curriculum", test_quiz_uses_curriculum),
        ("Unanswered = skipped", test_quiz_no_answer_is_skipped),
        ("Quiz stats scheduling/selection", test_quiz_stats_scheduling_and_selection),
        ("Question identity", test_question_identity),
        ("Mistake question id", test_mistake_question_id),
        ("Quiz stats file split", test_quiz_stats_file_split),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:  # noqa: BLE001
            # A test runner must report every failure instead of stopping at
            # the first one, so any exception is caught here on purpose.
            print(f"  ❌ {name}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Test results: {passed} passed / {failed} failed / {len(tests)} total")
    print(f"{'=' * 60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
