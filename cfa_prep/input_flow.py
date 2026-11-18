"""
CFA Prep CLI - Input flow module
Author: CodeBuddy AI Assistant
Purpose: One step machine for every question that is typed in, so that the ways
         back work the same everywhere: \\b goes one step back, \\r starts the
         question over and \\q leaves the session — in the question, in the
         table and in every field after it.
"""

from collections.abc import Callable
from enum import Enum

BACK = r"\b"       # one step back
RESTART = r"\r"    # the question starts over
QUIT = r"\q"       # leave the session

HINT = "(\\b = one step back, \\r = start over, \\q = leave)"


class Action(Enum):
    """What the reader asked for at a step."""

    NEXT = "next"
    BACK = "back"
    RESTART = "restart"
    QUIT = "quit"


class FinishSession(Exception):
    """The reader is done: the session ends without a new mistake."""


class SkipQuestion(Exception):
    """The reader does not want this question: it is skipped."""


class QuitSession(Exception):
    """The reader wants to leave the session."""


class RestartQuestion(Exception):
    """The question starts over: the same question is asked again."""


class Step:
    """
    One step of the flow: a key, a prompt and the way the value is read.

    The key is the name the answer is stored under.  The kind is "line" for a
    single line and "block" for the lines that are pasted and end with a blank
    line (the table, the question of a free-form mistake).

    on_value is called with the value and the value of the previous run of this
    step, before the value is kept; it may raise to end the session, to skip
    the question or to start it over.  on_done is called with the value and the
    previous one, and returns what is kept (the table is parsed there).

    keep_on_empty says that an empty answer keeps the value of the previous
    run: the table that was pasted before is not lost when the question is
    typed again.

    when says whether the step is asked at all: it is called with the answers
    that are already there (the caption of a card is only asked for when there
    is a picture).
    """

    key: str
    prompt: str
    kind: str
    on_value: Callable[[str, str], None] | None
    on_done: Callable[[str, str], str] | None
    keep_on_empty: bool
    when: Callable[[dict[str, str]], bool] | None

    def __init__(
        self,
        key: str,
        prompt: str,
        kind: str = "line",
        on_value: Callable[[str, str], None] | None = None,
        on_done: Callable[[str, str], str] | None = None,
        keep_on_empty: bool = False,
        when: Callable[[dict[str, str]], bool] | None = None,
    ) -> None:
        self.key = key
        self.prompt = prompt
        self.kind = kind
        self.on_value = on_value
        self.on_done = on_done
        self.keep_on_empty = keep_on_empty
        self.when = when


class StepFlow:
    """
    Asks the steps of one question and keeps the answers.

    The reader can always go one step back, start the question over or leave
    the session, whatever step it is on.  The answers are kept, so going back
    and typing the answer again only changes that one answer.
    """

    _prompt: Callable[[str], str]
    values: dict[str, str]
    index: int

    def __init__(self, prompt: Callable[[str], str]) -> None:
        self._prompt = prompt
        self.values = {}
        self.index = 0

    def run(self, steps: list[Step]) -> dict[str, str]:
        """Ask every step and return the answers."""
        while self.index < len(steps):
            step = steps[self.index]
            if not self._applies(step):
                # The step does not apply to what was answered so far
                self.index += 1
                continue
            action, value = self._read(step)
            if action is Action.BACK:
                self._back(steps)
                continue
            if action is Action.RESTART:
                self.values.clear()
                self.index = 0
                print("  🔄 Started over.")
                continue
            if action is Action.QUIT:
                raise QuitSession()
            previous = self.values.get(step.key, "")
            if step.on_value is not None:
                try:
                    step.on_value(value, previous)
                except RestartQuestion:
                    # The question starts over: the answers of the attempt that
                    # was refused are dropped.
                    self.values.clear()
                    self.index = 0
                    continue
            kept = step.on_done(value, previous) if step.on_done else value
            if not kept and previous and step.keep_on_empty:
                # The step is asked again and the answer is left empty: what was
                # typed before is kept.
                kept = previous
                print(f"  ↩️ Keeping the {step.key} from before.")
            self.values[step.key] = kept
            self.index += 1
        return self.values

    def _applies(self, step: Step) -> bool:
        """Tell whether the step is asked with what is answered so far."""
        return step.when is None or step.when(self.values)

    def _back(self, steps: list[Step]) -> None:
        """Go one step back, or say that there is no earlier step."""
        if self.index == 0:
            print("  ⚠️ Already at the first step.")
            return
        self.index -= 1
        # The steps that do not apply are stepped over
        while self.index > 0 and not self._applies(steps[self.index]):
            self.index -= 1
        print(f"  ⬅️ Back to: {steps[self.index].key}")

    def _read(self, step: Step) -> tuple[Action, str]:
        """Read the value of a step."""
        if step.kind == "block":
            return self._read_block(step)
        raw = self._prompt(step.prompt).strip()
        action = _escape(raw)
        if action is not None:
            return action, ""
        return Action.NEXT, raw

    def _read_block(self, step: Step) -> tuple[Action, str]:
        """Read the lines of a block; a blank line ends it."""
        lines: list[str] = []
        while True:
            line = self._prompt(step.prompt if not lines else "")
            if not line.strip():
                break
            if not lines:
                # The command can only be the first line of the block
                action = _escape(line.strip())
                if action is not None:
                    return action, ""
            lines.append(line)
        return Action.NEXT, "\n".join(lines)


def _escape(text: str) -> Action | None:
    """Return what the reader asked for, when the text is a command."""
    if text == BACK:
        return Action.BACK
    if text == RESTART:
        return Action.RESTART
    if text == QUIT:
        return Action.QUIT
    return None
