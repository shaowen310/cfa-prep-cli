"""
CFA Prep CLI - Tests for the mistake analyzer module
Author: CodeBuddy AI Assistant
Purpose: Check the mistake log: logging, attribution, the session summary, the browse view and the tables.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.curriculum import Curriculum
from cfa_prep.mistake_analyzer import MistakeAnalyzer
from cfa_prep.quiz_engine import QuizEngine


def test_mistake_analyzer():
    """Test the mistake analyzer"""
    analyzer = MistakeAnalyzer()
    stats = analyzer.get_mistake_stats()
    assert "total" in stats
    print(f"  ✅ Mistake analyzer is fine (mistakes: {stats['total']})")


def test_quiz_module_attribution():
    """Test that a mistake is attributed to its module, not to a typed topic"""
    import json
    import tempfile

    from cfa_prep.curriculum import module_group_of
    from cfa_prep.quiz_stats import RESULT_WRONG, UNSEEN_PRIORITY

    modules = [f"Module {i}: Basics" for i in range(1, 7)]
    data = {
        "L1": {
            "Economics": {
                mod: [f"{mod} topic {t}" for t in range(1, 4)] for mod in modules
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

            options = ["A tariff", "An import quota", "A voluntary export restraint"]
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question="Which trade restriction costs the importing country most?",
                user_answer=options[0],
                correct_answer=options[1],
                explanation="",
                module_name="Module 1: Basics",
                options=options,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert "key_point" not in records[0], "the typed topic must not be recorded"
            assert records[0]["module"] == "Module 1: Basics"
            # A mistake without a module cannot be attributed, so it is rejected
            try:
                _ = analyzer.add_mistake(
                    subject="Economics",
                    question="A question without a module",
                    user_answer=options[0],
                    correct_answer=options[1],
                    explanation="",
                    module_name="",
                    options=options,
                )
                raise AssertionError("a mistake without a module must be rejected")
            except ValueError:
                pass

            engine = QuizEngine()
            qid = records[0]["question_id"]
            group = "Economics > Module 1: Basics"

            # The module is the unit the quiz reviews: it carries the score
            scores = engine._module_scores()  # pyright: ignore[reportPrivateUsage]
            assert group in scores, "the module of the mistake must carry the score"
            assert "Economics > Module 2: Basics" not in scores, (
                "a mistake must not leak into another module"
            )

            # The mistake is replayed as a question of its module
            items = engine._get_mistake_questions()  # pyright: ignore[reportPrivateUsage]
            assert len(items) == 1
            assert items[0]["module"] == "Module 1: Basics"
            assert items[0]["question_id"] == qid

            # The material of the module follows the question
            material = engine._module_material(  # pyright: ignore[reportPrivateUsage]
                "L1", engine._modules_of(items)  # pyright: ignore[reportPrivateUsage]
            )
            assert len(material) == 1
            module_group, topics = material[0]
            assert module_group == group
            assert len(topics) == 3, "the whole topic list of the module is the material"
            assert all(module_group_of(t) == group for t in topics)

            # A wrong answer makes the module urgent
            engine.stats.record_question(
                qid, RESULT_WRONG, question=records[0]["question"], level="L1"
            )
            scores = engine._module_scores()  # pyright: ignore[reportPrivateUsage]
            assert scores[group] > UNSEEN_PRIORITY, (
                "a module with a wrong mistake must outrank an unseen module"
            )

            print("  ✅ A mistake is attributed to its module, not to a typed topic")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_question_identity():
    """Test the hashed question identity: stable, short and free of collisions"""
    import tempfile
    from datetime import date

    from cfa_prep.mistake_analyzer import question_id
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
    # A curriculum topic is not a question, so it has no identity of its own
    import cfa_prep.quiz_engine as qe
    assert not hasattr(qe, "curriculum_topic_id")

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            stats = QuizStats()
            today = date(2026, 1, 1)
            stats.record_question(
                qid, RESULT_WRONG, question=stem, level="L1",
                today=today,
            )
            # The same question asked again updates the same entry
            stats.record_question(
                qid, RESULT_CORRECT, question=stem, level="L1",
                today=today,
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


def test_mistake_upsert():
    """Test that a question that is logged again updates its record"""
    import json
    import tempfile

    question = "Which trade restriction costs the importing country most?"
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
                explanation="A quota costs the importing country the most.",
                module_name="Module 6: International Trade",
                options=options,
            )
            # The same question, logged again with another wrong answer
            _ = analyzer.add_mistake(
                subject="Economics",
                question=question,
                user_answer=options[2],
                correct_answer=options[1],
                explanation="",
                module_name="Module 6: International Trade",
                options=options,
            )

            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            # The log holds the question once
            assert len(records) == 1, records
            record = records[0]
            assert record.get("attempts") == 2, record
            assert record.get("last_date"), record
            # The last wrong answer is the one that was given
            assert record.get("user_answer") == options[2], record
            # Both wrong answers are kept
            assert record.get("wrong_answers") == [options[0], options[2]], record
            # What was written by hand is not wiped by an empty new attempt
            assert record.get("explanation"), record
            assert record.get("correct_answer") == options[1], record

            # A third attempt with the same answer does not repeat the history
            _ = analyzer.add_mistake(
                subject="Economics",
                question=question,
                user_answer=options[2],
                correct_answer=options[1],
                explanation="",
                module_name="Module 6: International Trade",
                options=options,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert len(records) == 1, records
            assert records[0].get("attempts") == 3, records[0]
            assert records[0].get("wrong_answers") == [options[0], options[2]], records[0]
            print("  ✅ A question that is logged again updates its record")
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
                explanation="",
                module_name="Module 6: International Trade",
                options=options,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert len(records) == 1
            stored = records[0].get("question_id", "")
            assert stored.startswith("q:"), "the record must carry a question id"
            assert stored == question_id(question, options), (
                "the id must be derived from the question text and its options"
            )

            # A re-logged copy updates the record instead of writing a second one
            _ = analyzer.add_mistake(
                subject="Economics",
                question=question,
                user_answer=options[0],
                correct_answer=options[1],
                explanation="",
                module_name="Module 6: International Trade",
                options=options,
                existing_question_id=stored,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert len(records) == 1, "the log must not grow with every attempt"
            assert records[0]["question_id"] == stored, (
                "a re-logged mistake must keep the id of the original question"
            )
            assert records[0].get("attempts") == 2, records[0]

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


def test_mistake_session_summary():
    """Test that the logging session ends with a line stating how many mistakes were saved"""
    import io
    import json
    import tempfile
    from contextlib import redirect_stdout

    from cfa_prep.mistake_analyzer import MistakeAnalyzer

    question = "Which trade restriction is likely to result in the greatest welfare loss?"
    options = ["A tariff", "An import quota", "A voluntary export restraint"]
    answers = [
        "Economics",                         # subject
        "Module 6: International Trade",     # module
        question,                            # question text
        "",                                  # no table below the question
        options[0],                          # option A
        options[1],                          # option B
        options[2],                          # option C
        "A",                                 # the wrong answer
        "B",                                 # the correct answer
        "",                                  # explanation (optional)
        "",                                  # a blank question ends the session
    ]

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        answer_iter = iter(answers)

        def fake_prompt(prompt: str = "") -> str:
            del prompt  # the scripted answers do not depend on the prompt
            return next(answer_iter, "")

        original_prompt = MistakeAnalyzer._prompt  # pyright: ignore[reportPrivateUsage]
        MistakeAnalyzer._prompt = staticmethod(fake_prompt)  # pyright: ignore[reportPrivateUsage]
        try:
            analyzer = MistakeAnalyzer()
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                analyzer.add_mistake_interactive(None, "L1")
            output = buffer.getvalue()
            assert (
                "✅ Session complete — 1 mistake saved for "
                "Economics > Module 6: International Trade." in output
            ), output
            assert "Mistake log by subject and module" not in output, output
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert len(records) == 1, "the count in the summary must match what was saved"
            print("  ✅ The session states how many mistakes were saved")
        finally:
            MistakeAnalyzer._prompt = staticmethod(original_prompt)  # pyright: ignore[reportPrivateUsage]
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_mistake_browse():
    """Test that the questions of a module can be browsed by subject and module"""
    import io
    import tempfile
    from contextlib import redirect_stdout

    from cfa_prep.mistake_analyzer import MistakeAnalyzer

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            analyzer = MistakeAnalyzer()
            for question, correct in (
                (
                    "Which trade restriction costs the importing country most?",
                    "An import quota",
                ),
                (
                    "Which restriction is voluntary?",
                    "A voluntary export restraint",
                ),
            ):
                _ = analyzer.add_mistake(
                    subject="Economics",
                    question=question,
                    user_answer="A tariff",
                    correct_answer=correct,
                    explanation="The quota raises the domestic price.",
                    module_name="Module 6: International Trade",
                    options=[
                        "An import quota",
                        "A tariff",
                        "A voluntary export restraint",
                    ],
                )
            _ = analyzer.add_mistake(
                subject="Equity",
                question="What is the beta of a defensive stock?",
                user_answer="1.5",
                correct_answer="0.8",
                explanation="",
                module_name="Module 1: Overview of Equity Securities",
                options=["0.8", "1.5", "2.0"],
            )

            answers = iter(["1", "1"])  # subject 1 (Economics), module 1
            original_prompt = MistakeAnalyzer._prompt  # pyright: ignore[reportPrivateUsage]

            def fake_prompt(prompt: str = "") -> str:
                del prompt  # the scripted answers do not depend on the prompt
                return next(answers, "")

            MistakeAnalyzer._prompt = staticmethod(fake_prompt)  # pyright: ignore[reportPrivateUsage]
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    analyzer.browse_mistakes()
            finally:
                MistakeAnalyzer._prompt = staticmethod(original_prompt)  # pyright: ignore[reportPrivateUsage]
            output = buffer.getvalue()
            assert "Subject:" in output, output
            assert "[1] Economics (2)" in output, output
            assert "Module:" in output, output
            assert "[1] Module 6: International Trade (2)" in output, output
            assert "Which trade restriction costs the importing country most?" in output, output
            # The answer is named on its own line, the options stay clean
            # ("An import quota" is the first option, the restraint the third)
            assert "Answer: A" in output, output
            assert "Answer: C" in output, output
            # While browsing, the answer that was chosen is not shown
            assert "Your answer" not in output, output
            print("  ✅ The questions of a module can be browsed by subject and module")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_print_mistake_hides_the_wrong_answer():
    """Test that the browse view shows the correct answer only"""
    import io
    import tempfile
    from contextlib import redirect_stdout

    from cfa_prep.mistake_analyzer import MistakeAnalyzer

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            analyzer = MistakeAnalyzer()
            # A free-form mistake, so the answers are printed as text
            _ = analyzer.add_mistake(
                subject="Economics",
                question="What is the impact of a tariff on the domestic price?",
                user_answer="4.2%",
                correct_answer="4.0%",
                explanation="",
                module_name="Module 2: Policy",
            )
            record = analyzer.all_mistakes()[-1]

            # The full view shows both answers
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                analyzer.print_mistake(record)
            assert "Your answer: 4.2%" in buffer.getvalue(), buffer.getvalue()
            assert "Answer: 4.0%" in buffer.getvalue(), buffer.getvalue()

            # The browse view shows the correct answer only
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                analyzer.print_mistake(record, show_wrong=False)
            output = buffer.getvalue()
            assert "Your answer" not in output, output
            assert "Answer: 4.0%" in output, output
            print("  ✅ The browse view shows the correct answer only")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_ctrl_c_exits_gracefully():
    """Test that Ctrl+C ends a command without a traceback"""
    import io
    import tempfile
    from contextlib import redirect_stdout

    from cfa_prep.mistake_analyzer import MistakeAnalyzer

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Economics",
                question="Which trade restriction costs the importing country most?",
                user_answer="A tariff",
                correct_answer="An import quota",
                explanation="",
                module_name="Module 6: International Trade",
                options=["An import quota", "A tariff", "A voluntary export restraint"],
            )

            def interrupted(prompt: str = "") -> str:
                del prompt
                raise KeyboardInterrupt

            original_prompt = MistakeAnalyzer._prompt  # pyright: ignore[reportPrivateUsage]
            MistakeAnalyzer._prompt = staticmethod(interrupted)  # pyright: ignore[reportPrivateUsage]
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    analyzer.browse_mistakes()
            finally:
                MistakeAnalyzer._prompt = staticmethod(original_prompt)  # pyright: ignore[reportPrivateUsage]
            output = buffer.getvalue()
            assert "Traceback" not in output, output
            assert "(cancelled)" in output, output
            print("  ✅ Ctrl+C ends the command without a traceback")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_mistake_with_table():
    """Test that a table can be attached to a mistake and is stored with it"""
    import json
    import tempfile

    from cfa_prep.tables import parse_table, render_table

    pasted = [
        "\tYear 1\tYear 2",
        "Days sales outstanding\t85\t76",
        "Days of inventory on hand\t136\t129",
        "Days payable outstanding\t29\t13",
    ]
    table = parse_table(pasted)
    assert table is not None
    assert table["header"] == ["", "Year 1", "Year 2"], table
    assert len(table["rows"]) == 3, table
    assert table["rows"][0] == ["Days sales outstanding", "85", "76"], table

    lines = render_table(table, indent="  ")
    assert len(lines) == 5, lines  # header + rule + three rows
    assert lines[2].strip().startswith("Days sales outstanding"), lines
    assert lines[2].strip().endswith("76"), lines

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            analyzer = MistakeAnalyzer()
            _ = analyzer.add_mistake(
                subject="Financial Statement Analysis",
                question="Based on the table, which ratio improved the most?",
                user_answer="Days payable outstanding",
                correct_answer="Days sales outstanding",
                explanation="",
                module_name="Module 2: Analyzing Income Statements",
                options=[
                    "Days sales outstanding",
                    "Days of inventory on hand",
                    "Days payable outstanding",
                ],
                table=table,
            )
            records = json.loads(analyzer.data_file.read_text(encoding="utf-8"))["records"]
            assert records[0]["table"]["header"] == ["", "Year 1", "Year 2"], records
            assert len(records[0]["table"]["rows"]) == 3, records
            print("  ✅ A table can be attached to a mistake")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_mistake_breakdown_view():
    """Test that `cfa-prep mis` shows the mistake log by subject and module, in curriculum order"""
    import io
    import tempfile
    from contextlib import redirect_stdout
    from types import SimpleNamespace

    from cfa_prep.curriculum import Curriculum
    from cfa_prep.main import cmd_mistake
    from cfa_prep.mistake_analyzer import MistakeAnalyzer

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            # The curriculum defines the order of the exam
            curriculum = Curriculum()
            curriculum.save({
                "L1": {
                    "Fixed Income": {
                        "Module 1: Fixed-Income Instrument Features": ["Topic A"],
                        "Module 2: Fixed-Income Valuation": ["Topic B"],
                    },
                    "Economics": {
                        "Module 6: International Trade": ["Topic C"],
                    },
                }
            })

            analyzer = MistakeAnalyzer()
            for question in ("What is a tariff?", "What is an import quota?"):
                _ = analyzer.add_mistake(
                    subject="Economics",
                    question=question,
                    user_answer="An import quota",
                    correct_answer="A tariff",
                    explanation="",
                    module_name="Module 6: International Trade",
                    options=["A tariff", "An import quota", "A voluntary export restraint"],
                )
            _ = analyzer.add_mistake(
                subject="Fixed Income",
                question="What is duration?",
                user_answer="A tax",
                correct_answer="A weighted average maturity",
                explanation="",
                module_name="Module 1: Fixed-Income Instrument Features",
                options=["A tax", "A weighted average maturity", "A subsidy"],
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                cmd_mistake(SimpleNamespace(add=False, browse=False))  # pyright: ignore[reportArgumentType]
            output = buffer.getvalue()
            assert "Mistake log by subject and module (3 mistakes)" in output, output
            # The count comes first, right-aligned on the width of the largest one
            assert "  2 | Economics > Module 6: International Trade" in output, output
            assert (
                "  1 | Fixed Income > Module 1: Fixed-Income Instrument Features" in output
            ), output
            # The curriculum order wins over the number of mistakes
            fixed_income = output.index("Fixed Income > Module 1")
            economics = output.index("Economics > Module 6")
            assert fixed_income < economics, output
            print("  ✅ The mistake view shows the log in curriculum order")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)
