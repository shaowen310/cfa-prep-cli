"""
CFA Prep CLI - Tests for the quiz engine module
Author: CodeBuddy AI Assistant
Purpose: Check the quiz engine: the mistake review, the module material and the question statistics.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.curriculum import Curriculum
from cfa_prep.mistake_analyzer import MistakeAnalyzer
from cfa_prep.quiz_engine import QuizEngine


def test_quiz_engine():
    """Test the quiz engine"""
    engine = QuizEngine()
    modules = engine._module_review("L1", [])  # pyright: ignore[reportPrivateUsage]
    assert isinstance(modules, list)
    material = engine._module_material("L1", modules)  # pyright: ignore[reportPrivateUsage]
    assert len(material) == len(modules)
    print(f"  ✅ Quiz engine is fine (L1 module review: {len(material)} module(s))")


def test_module_review_follows_the_questions():
    """Test that the material under review is the material of the modules asked about"""
    import json
    import tempfile

    from cfa_prep.curriculum import module_group_of

    data = {
        "L1": {
            "Economics": {
                "Module 1: Basics": ["A", "B", "C"],
                "Module 2: Policy": ["D", "E", "F"],
            }
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            c = Curriculum()
            _ = c.seed()
            src = Path(tmp) / "cur.json"
            _ = src.write_text(json.dumps(data), encoding="utf-8")
            c.import_file(str(src))

            # Without any mistake the review still gives material to work on
            engine = QuizEngine()
            modules = engine._module_review("L1", [])  # pyright: ignore[reportPrivateUsage]
            assert len(modules) == 1, "one module without mistakes is added"
            material = engine._module_material("L1", modules)  # pyright: ignore[reportPrivateUsage]
            assert len(material) == 1
            assert len(material[0][1]) == 3, "the whole topic list of the module is shown"

            # The material follows the modules the questions came from
            options = ["A tariff", "An import quota", "A voluntary export restraint"]
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question="Which trade restriction costs the importing country most?",
                user_answer=options[0],
                correct_answer=options[1],
                explanation="",
                module_name="Module 2: Policy",
                options=options,
            )
            engine = QuizEngine()
            items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
            assert len(items) == 1
            review = engine._module_review("L1", engine._modules_of(items))  # pyright: ignore[reportPrivateUsage]
            assert "Economics > Module 2: Policy" in review
            assert len(review) == 2, "the module of the question plus one without mistakes"
            material = engine._module_material("L1", review)  # pyright: ignore[reportPrivateUsage]
            for module_group, topics in material:
                assert topics, f"every module under review must have material: {module_group}"
                assert all(module_group_of(t) == module_group for t in topics)

            print("  ✅ The material under review follows the questions")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_mistake_replay_module_cap():
    """Test that the mistake review holds at most two questions per module"""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            data = {
                "L1": {
                    "Economics": {
                        "Module 1: Basics": ["Topic A"],
                        "Module 2: Policy": ["Topic B"],
                    }
                }
            }
            c = Curriculum()
            _ = c.seed()
            src = Path(tmp) / "cur.json"
            _ = src.write_text(json.dumps(data), encoding="utf-8")
            c.import_file(str(src))

            analyzer = MistakeAnalyzer()
            options = ["A tariff", "An import quota", "A voluntary export restraint"]
            # Four mistakes in one module, one in another
            for i in range(4):
                _ = analyzer.add_mistake(
                    subject="Economics",
                    question=f"A question of module one ({i})",
                    user_answer=options[0],
                    correct_answer=options[1],
                    explanation="",
                    module_name="Module 1: Basics",
                    options=options,
                )
            _ = analyzer.add_mistake(
                subject="Economics",
                question="A question of module two",
                user_answer=options[0],
                correct_answer=options[1],
                explanation="",
                module_name="Module 2: Policy",
                options=options,
            )

            engine = QuizEngine()
            items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
            counts: dict[str, int] = {}
            for item in items:
                key = f"{item['subject']} > {item['module']}"
                counts[key] = counts.get(key, 0) + 1
            assert counts.get("Economics > Module 1: Basics", 0) == 2, (
                "at most two questions of one module may be replayed"
            )
            assert counts.get("Economics > Module 2: Policy", 0) == 1, (
                "the other module must still be reviewed"
            )
            assert len(items) == 3, "the cap must not drop the other modules"

            # The limit can be raised when a module is the only source
            items = engine._get_mistake_questions(  # pyright: ignore[reportPrivateUsage]
                limit=10, limit_per_module=5
            )
            assert len(items) == 5, "a higher per-module limit takes more questions"

            print("  ✅ The mistake review holds at most two questions per module")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_quiz_records_only_questions():
    """Test that only real questions are recorded: a topic prompt is not a question"""
    import json
    import tempfile

    from cfa_prep.mistake_analyzer import MistakeAnalyzer
    from cfa_prep.quiz_stats import RESULT_SKIPPED, QuizStats

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

            # 1. The L1 flow: the topic prompts create no record at all
            engine = QuizEngine()
            engine._do_l1_quiz("L1")  # pyright: ignore[reportPrivateUsage]
            assert engine.stats.load()["questions"] == {}, (
                "a topic prompt is not a question and must not be recorded"
            )

            # 2. The L2 flow: the sub-question prompts create no record either
            engine = QuizEngine()
            engine._do_l2_quiz("L2")  # pyright: ignore[reportPrivateUsage]
            assert engine.stats.load()["questions"] == {}, (
                "a sub-question prompt must not be recorded"
            )

            # 3. The mistake replay: the question is recorded, and an unanswered
            #    mistake is skipped, never wrong
            analyzer = MistakeAnalyzer()
            options = ["A tariff", "An import quota", "A voluntary export restraint"]
            _ = analyzer.add_mistake(
                subject="Economics",
                question="Which trade restriction costs the importing country most?",
                user_answer=options[0],
                correct_answer=options[1],
                explanation="",
                module_name="Module 6: International Trade",
                options=options,
            )
            engine = QuizEngine()
            items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
            assert len(items) == 1
            _ = engine._run_mistake_mcq(items[0])  # pyright: ignore[reportPrivateUsage]
            assert engine.wrong == 0, "an unanswered mistake must not be wrong"
            assert engine.skipped == 1, "the unanswered mistake must be skipped"
            questions = QuizStats().load()["questions"]
            assert list(questions) == [items[0]["question_id"]], (
                "only the mistake question may be in the statistics"
            )
            stat = questions[items[0]["question_id"]]
            assert stat["last_result"] == RESULT_SKIPPED
            assert stat["times_wrong"] == 0
            assert stat["times_skipped"] == 1

            print("  ✅ Only questions are recorded - a topic prompt is not a question")
        finally:
            qe.read_input = original_read_input
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_quiz_stores_the_chosen_answer():
    """Test that a mistake created by the quiz keeps the answer that was chosen"""
    import tempfile

    import cfa_prep.quiz_engine as qe
    from cfa_prep.mistake_analyzer import MistakeAnalyzer

    options = ["A tariff", "An import quota", "A voluntary export restraint"]
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        original_read_input = qe.read_input
        qe.read_input = lambda prompt="": "A"  # always the first option shown

        try:
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question="Which trade restriction costs the importing country most?",
                user_answer=options[0],
                correct_answer=options[1],
                explanation="",
                module_name="Module 6: International Trade",
                options=options,
            )
            before = len(analyzer.all_mistakes())

            engine = QuizEngine()
            engine.randomize = False  # the options keep their order
            items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
            assert len(items) == 1
            _ = engine._run_mistake_mcq(items[0])  # pyright: ignore[reportPrivateUsage]

            records = analyzer.all_mistakes()
            # The record is updated, so the log does not grow
            assert len(records) == before, "the log must not grow with every attempt"
            logged = records[-1]
            # The quiz knows which answer was chosen, so it is stored
            assert logged.get("user_answer") == options[0], logged
            assert logged.get("correct_answer") == options[1], logged
            # The attempt is counted on the record that was already there
            assert logged.get("attempts") == 2, logged
            print("  ✅ The quiz stores the answer that was chosen")
        finally:
            qe.read_input = original_read_input
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_quiz_stats_scheduling_and_selection():
    """Test the quiz statistics: scheduling, mastery discount and priority selection"""
    import tempfile
    from datetime import date, timedelta

    from cfa_prep.mistake_analyzer import question_id
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
            wrong_question = "Which of the following best values a stock?"
            good_question = "Which of the following describes a bond?"
            unseen_question = "Which of the following describes an index?"

            # A wrong answer keeps the question due immediately
            wrong_id = question_id(wrong_question)
            stats.record_question(wrong_id, RESULT_WRONG, question=wrong_question, today=today)
            data = stats.load()
            stat = data["questions"][wrong_id]
            assert stat["times_wrong"] == 1
            assert stat["streak"] == 0
            assert stat["interval_days"] == 0
            assert next_due_of(stat) == today, "a wrong answer must be due again now"
            assert "next_due" not in stat, "the due date must be derived, not stored"
            assert "topic" not in stat, "the topic is not stored with the question"

            # A correct answer pushes the question into the future
            good_id = question_id(good_question)
            stats.record_question(good_id, RESULT_CORRECT, question=good_question, today=today)
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
                    question=good_question,
                    today=today + timedelta(days=day_offset),
                )
            stat = stats.load()["questions"][good_id]
            assert stat["streak"] == 4
            assert stat["interval_days"] == 14, "the interval ladder should reach 14 days"

            # Priority: the wrong question outranks the mastered one; unseen ones rank high
            p_wrong = stats.priority_of(wrong_id, today=today)
            p_good = stats.priority_of(good_id, today=today)
            p_unseen = stats.priority_of(question_id(unseen_question), today=today)
            assert p_wrong > p_good, "repeatedly wrong questions must have a higher priority"
            assert p_unseen > p_wrong, "never tested questions must have a high priority"
            assert p_good < 0, "a mastered question must be pushed back by the mastery discount"

            # Selection must favour the weak questions over the mastered one
            candidates = [wrong_question, good_question, unseen_question]
            import random as _random
            _random.seed(42)
            scored = [
                (stats.priority_of(question_id(t), today=today), t)
                for t in candidates
            ]
            selected = stats.select_scored(scored, 2)
            assert len(selected) == 2
            assert unseen_question in selected, "unseen questions should be selected first"
            assert wrong_question in selected, "repeatedly wrong questions should be selected"
            assert good_question not in selected, "a mastered question should be pushed back"

            # A skipped question was never really tested, so it must stay due
            skipped_question = "Which of the following describes a derivative?"
            skipped_id = question_id(skipped_question)
            stats.record_question(
                skipped_id, RESULT_SKIPPED, question=skipped_question, today=today
            )
            stat = stats.load()["questions"][skipped_id]
            assert stat["interval_days"] == 0, "a skipped question must be due again immediately"
            assert stats.priority_of(skipped_id, today=today) > 0, (
                "a skipped question must keep some priority"
            )

            print("  ✅ Quiz stats scheduling and priority selection work")
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
