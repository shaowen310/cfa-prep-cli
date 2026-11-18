"""
CFA Prep CLI - Tests for the input flow module
Author: CodeBuddy AI Assistant
Purpose: Check the step machine: the steps are asked in order, going back asks
         the earlier step again, starting over drops the answers, leaving ends
         the session and the answers that are kept.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.input_flow import (
    FinishSession,
    QuitSession,
    SkipQuestion,
    Step,
    StepFlow,
)


def _reader(values: list[str]):
    """Return a prompt that gives the answers one after the other."""
    answers = iter(values)
    return lambda prompt="": next(answers, "")


def test_step_flow_asks_every_step():
    """Test that the steps are asked in order and the answers are kept"""
    flow = StepFlow(_reader(["first", "second", "third"]))
    steps = [Step("a", "A: "), Step("b", "B: "), Step("c", "C: ")]
    values = flow.run(steps)
    assert values == {"a": "first", "b": "second", "c": "third"}, values
    print("  ✅ The steps are asked in order and the answers are kept")


def test_step_flow_goes_back():
    """Test that going back asks the earlier step again"""
    flow = StepFlow(_reader(["first", r"\b", "first again", "second"]))
    steps = [Step("a", "A: "), Step("b", "B: ")]
    values = flow.run(steps)
    assert values == {"a": "first again", "b": "second"}, values
    print("  ✅ Going back asks the earlier step again")


def test_step_flow_stops_at_the_first_step():
    """Test that there is no earlier step than the first one"""
    flow = StepFlow(_reader([r"\b", "first"]))
    steps = [Step("a", "A: "), Step("b", "B: ")]
    values = flow.run(steps)
    assert values["a"] == "first", values
    print("  ✅ There is no earlier step than the first one")


def test_step_flow_starts_over():
    """Test that starting over drops the answers"""
    flow = StepFlow(_reader(["first", r"\r", "new question", "second"]))
    steps = [Step("a", "A: "), Step("b", "B: ")]
    values = flow.run(steps)
    assert values == {"a": "new question", "b": "second"}, values
    print("  ✅ Starting over drops the answers")


def test_step_flow_leaves_the_session():
    """Test that leaving ends the session"""
    flow = StepFlow(_reader(["first", r"\q"]))
    steps = [Step("a", "A: "), Step("b", "B: ")]
    try:
        _ = flow.run(steps)
    except QuitSession:
        pass
    else:
        raise AssertionError("leaving must end the session")
    print("  ✅ Leaving ends the session")


def test_step_flow_reads_a_block():
    """Test that a block ends with a blank line"""
    flow = StepFlow(_reader(["first line", "second line", "", "after"]))
    steps = [Step("block", "Block: ", kind="block"), Step("a", "A: ")]
    values = flow.run(steps)
    assert values["block"] == "first line\nsecond line", values
    assert values["a"] == "after", values
    print("  ✅ A block ends with a blank line")


def test_step_flow_keeps_the_answer_of_before():
    """Test that an empty answer keeps what was typed before"""
    flow = StepFlow(_reader(["first", r"\b", ""]))
    steps = [Step("a", "A: ", keep_on_empty=True), Step("b", "B: ")]
    values = flow.run(steps)
    assert values["a"] == "first", values
    print("  ✅ An empty answer keeps what was typed before")


def test_step_flow_can_end_and_skip():
    """Test that a step can end the session or skip the question"""
    def finish(value: str, previous: str) -> None:
        """Refuse the value: the session ends."""
        del value, previous
        raise FinishSession

    def skip(value: str, previous: str) -> None:
        """Refuse the value: the question is skipped."""
        del value, previous
        raise SkipQuestion

    flow = StepFlow(_reader([""]))
    try:
        _ = flow.run([Step("a", "A: ", on_value=finish)])
    except FinishSession:
        pass
    else:
        raise AssertionError("the session must end")

    flow = StepFlow(_reader([""]))
    try:
        _ = flow.run([Step("a", "A: ", on_value=skip)])
    except SkipQuestion:
        pass
    else:
        raise AssertionError("the question must be skipped")
    print("  ✅ A step can end the session or skip the question")


def test_step_flow_skips_a_step_that_does_not_apply():
    """Test that a step is not asked when it does not apply"""
    flow = StepFlow(_reader(["first", "second"]))
    steps = [
        Step("a", "A: "),
        Step(
            "b",
            "B: ",
            # The second step only applies to another answer
            when=lambda values: values.get("a", "").strip() == "other",
        ),
    ]
    values = flow.run(steps)
    assert values == {"a": "first"}, values
    print("  ✅ A step is not asked when it does not apply")
