"""
CFA Prep CLI - Mistake analyzer module
Author: CodeBuddy AI Assistant
Purpose: Log and analyze mistakes, stored in an SQLite database at
         <data_root>/mistakes/mistakes.db.
         Supports MCQ (L1) and free-form (L2/L3) mistake logging.
"""

from pathlib import Path
from typing import cast

from .curriculum import Curriculum
from .input_flow import (
    BACK,
    HINT,
    QUIT,
    FinishSession,
    QuitSession,
    RestartQuestion,
    SkipQuestion,
    Step,
    StepFlow,
)
from .mistake_store import (
    DB_NAME,
    MAX_WRONG_ANSWERS,
    MistakeRecord,
    MistakeStore,
    reconcile_options,
)
from .tables import Table, render_table, table_from_text
from .utils import (
    get_data_dir,
    hash_text,
    normalize_text,
    print_section,
    today_str,
)

QUESTION_PREFIX = "q:"   # identity derived from the question text


def question_id(stem: str, options: list[str] | None = None) -> str:
    """
    Return the stable id of a question.

    The id is a hash of the question text plus its options.  Hashing keeps the
    stored key short (18 characters instead of the whole question) and makes it
    immune to formatting changes, while the options are part of the identity
    because two different questions can share the same stem.

    The options are hashed in sorted order, so the identity does not depend on
    the order the options happen to be displayed in.

    The correct answer is deliberately NOT part of the id, so re-logging a
    question with a corrected answer keeps its history attached.
    """
    normalized = sorted(normalize_text(option) for option in (options or []))
    return QUESTION_PREFIX + hash_text(stem, "\n".join(normalized))


def _session_label(subject: str, module_name: str) -> str:
    """
    Return the "Subject > Module" label of a mistake-logging session.

    Either part may be missing, so the label falls back to whichever one is
    known and is empty when neither is.
    """
    if subject and module_name:
        return f"{subject} > {module_name}"
    return subject or module_name


class MistakeAnalyzer:
    """
    Mistake analyzer.
    Manages the entry, categorization, storage, and retrieval of mistakes.
    All records are stored in an SQLite database (mistakes.db).
    """

    def __init__(self):
        self.mistakes_dir: Path = get_data_dir("mistakes")
        self.db_file: Path = self.mistakes_dir / DB_NAME
        self.store: MistakeStore = MistakeStore(self.db_file)

    def _load(self) -> list[MistakeRecord]:
        """Load all mistake records."""
        return self.store.load_all()

    def _save(self, records: list[MistakeRecord]) -> None:
        """Save all mistake records."""
        self.store.replace_all(records)

    def _find_duplicates(self, question: str) -> list[MistakeRecord]:
        """
        Find previously logged mistakes whose question text matches the given one
        (case-insensitive). Used to warn the user before re-adding a question,
        since the same title may have different options.
        """
        if not question.strip():
            return []
        return self.store.load_by_question(question.strip())

    def _confirm_duplicate(self, question: str) -> bool:
        """
        If the question was already logged, show the full previous record(s) and
        ask whether to continue adding anyway. Returns True to proceed, False to skip.
        """
        dups = self._find_duplicates(question)
        if not dups:
            return True
        print("\n  ⚠️  This question was already logged before:")
        for i, r in enumerate(dups, 1):
            print(f"  {'─' * 46}")
            print(f"  [{i}] {r.get('question', '')}")
            options = r.get("options") or []
            if options:
                for letter, opt in zip("ABC", options):
                    print(f"      {letter}. {opt}")
            table = r.get("table")
            if table:
                for row in render_table(table, indent="      "):
                    print(row)
            if r.get("correct_answer"):
                print(f"      ✅ Correct: {r['correct_answer']}")
            if r.get("date"):
                print(f"      🗓 Date: {r['date']}")
        choice = self._prompt("\nLog it again? The record is updated. [y/N]: ").strip().lower()
        return choice in ("y", "yes")

    def add_mistake(
        self,
        subject: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        explanation: str,
        module_name: str = "",
        level: str = "L1",
        options: list[str] | None = None,
        existing_question_id: str = "",
        table: Table | None = None,
    ) -> str:
        """
        Add a mistake record to the mistake log (mistakes.db).

        A question that is already logged is updated instead of being written a
        second time: the attempt is counted, the date of the last attempt is
        kept and the wrong answers are collected.  The log therefore grows with
        the questions, not with the attempts.

        Parameters:
            subject: subject name (e.g., Economics)
            question: question text (without options)
            user_answer: the user's incorrect answer
            correct_answer: the correct answer
            explanation: the explanation of the correct answer
            module_name: module within the subject (required)
            level: exam level (L1/L2/L3)
            options: list of option texts [A, B, C] for MCQ (optional)
            existing_question_id: id of an already known question (e.g. when a
                record is re-logged); when empty it is derived from the question
                text and options
            table: the table the question refers to (optional)

        Returns:
            the path of the mistakes database
        """
        # The subject and module are curriculum values, so they are the reliable
        # link between a mistake and the material it belongs to.  A mistake
        # without a module cannot be attributed, so it is rejected.
        if not module_name.strip():
            raise ValueError("A mistake needs a module to belong to.")
        # The question id is created once, here, and stored with the record.
        # Everything downstream reads it from the log, so the id of a
        # question is never derived twice from different texts.
        qid = existing_question_id.strip()
        if not qid and question.strip():
            qid = question_id(question, options or [])
        record = MistakeRecord(
            date=today_str(),
            level=level,
            subject=subject,
            module=module_name,
            question=question,
            question_id=qid,
            options=options or [],
            user_answer=user_answer,
            correct_answer=correct_answer,
            explanation=explanation,
        )
        if table:
            record["table"] = table

        # A question that is already logged is updated, not written a second
        # time: the log grows with the questions, not with the attempts.
        existing = self.store.get(qid)
        if existing is None:
            # The question may already be logged under a slightly different
            # text (a trailing colon, another spacing).  It is the same
            # question, so the record that is already there is updated and its
            # id is kept — the quiz statistics stay attached to it.
            existing = self._matching_record(question, options or [])
        if existing is None:
            record["attempts"] = 1
            if record.get("user_answer"):
                # The history of the wrong answers starts with this one
                record["wrong_answers"] = [record["user_answer"]]
            self.store.upsert(record)
        else:
            self._update_mistake(existing, record)
            self.store.upsert(existing)
        return str(self.db_file)

    def _matching_record(
        self, question: str, options: list[str]
    ) -> MistakeRecord | None:
        """
        Return the record of the question that is already logged, if it is the
        same question.

        The question text is matched on its key, so a trailing colon or another
        spacing does not hide the record that is already there.  The options
        decide between several questions that share the same stem.
        """
        if not question.strip():
            return None
        candidates = self.store.load_by_question(question)
        if not candidates:
            return None
        wanted = sorted(normalize_text(option) for option in options)
        for record in candidates:
            stored = sorted(
                normalize_text(option) for option in (record.get("options") or [])
            )
            if stored == wanted:
                return record
        if len(candidates) == 1:
            # One question with this stem is logged and its options were typed
            # again: it is the question the user confirmed in the prompt.
            return candidates[0]
        # Several questions share the stem: none of them is clearly the one.
        return None

    @staticmethod
    def _find_by_id(
        records: list[MistakeRecord], qid: str
    ) -> MistakeRecord | None:
        """Return the record of that question, when it is already logged."""
        if not qid:
            return None
        for record in records:
            if record.get("question_id") == qid:
                return record
        return None

    @staticmethod
    def _update_mistake(existing: MistakeRecord, new: MistakeRecord) -> None:
        """
        Fold a new attempt into the record that is already there.

        What was typed by hand (the explanation, the options, the table) is kept
        when the new attempt does not bring it, so an automatic entry (the quiz
        re-logging a repeated mistake) never wipes what the user wrote.
        """
        existing["attempts"] = existing.get("attempts", 1) + 1
        existing["last_date"] = new.get("date", "")

        wrong = new.get("user_answer", "")
        if wrong:
            existing["user_answer"] = wrong
            # The history holds the answers that were wrong, each one once: it
            # shows the traps that were taken, not every single attempt.
            history = list(existing.get("wrong_answers") or [])
            if wrong not in history:
                history.append(wrong)
            existing["wrong_answers"] = history[-MAX_WRONG_ANSWERS:]

        correct = new.get("correct_answer", "")
        if correct and correct != existing.get("correct_answer"):
            existing["correct_answer"] = correct
        if new.get("explanation"):
            existing["explanation"] = new["explanation"]
        options = new.get("options")
        if options:
            # The options are matched on their key: a text that ends with
            # punctuation wins over the same text without it
            merged_options, mapping = reconcile_options(
                existing.get("options") or [], list(options)
            )
            existing["options"] = merged_options
            # The answers are written the way the options they belong to are
            wrong_text = existing.get("user_answer", "")
            if wrong_text:
                existing["user_answer"] = mapping.get(wrong_text, wrong_text)
            correct_text = existing.get("correct_answer", "")
            if correct_text:
                existing["correct_answer"] = mapping.get(correct_text, correct_text)
        table = new.get("table")
        if table:
            existing["table"] = table

    @staticmethod
    def _prompt(prompt: str = "") -> str:
        """
        Read a line of input.  On Ctrl+C / EOF, re-raises so the outer
        handler in add_mistake_interactive can abort cleanly.
        """
        try:
            return input(prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            raise

    def add_mistake_interactive(
        self, curriculum: Curriculum | None = None, level: str = "L1"
    ) -> None:
        """
        Interactively log a mistake.
        For L1 (MCQ mode): streamlined single-question, A/B/C answers.
        For L2/L3: free-text question description, answers, explanation.
        The subject and module are required: they are the curriculum values that
        tie a mistake to the material it belongs to.
        Exits gracefully if the user stops inputting (Ctrl+C / Ctrl+D).
        """
        saved = 0
        subject = ""
        module_name = ""
        try:
            print("\n" + "=" * 50)
            is_mcq = level.upper() == "L1"
            if is_mcq:
                print("  📝 Log a Mistake (MCQ)")
            else:
                print("  📝 Log a Mistake")
            print("=" * 50)

            module_name = ""
            if curriculum:
                subject, module_name = self._pick_subject_and_module(curriculum, level)
                if not subject or not module_name:
                    print("❌ A subject and module are required to log a mistake.")
                    return
            else:
                subject = self._prompt("Subject (e.g., FRA, Equity, Ethics): ").strip()
                if not subject:
                    print("❌ Subject cannot be empty")
                    return
                module_name = self._prompt(
                    "Module (e.g., Module 3: Fiscal Policy): "
                ).strip()
                if not module_name:
                    print("❌ Module cannot be empty - a mistake must belong to a module.")
                    return

            if is_mcq:
                first = True
                while True:
                    result = self._log_mcq(
                        subject, module_name, level, show_hint=first
                    )
                    first = False
                    if result == "finished":
                        break
                    if result == "quit":
                        print("\n  👋 Left the session.")
                        break
                    if result == "saved":
                        saved += 1
            else:
                if self._log_freeform(subject, module_name, level):
                    saved += 1

        except (KeyboardInterrupt, EOFError):
            print("\n\n⚠️  Aborted — current mistake was NOT saved.")
            if saved > 0:
                noun = "mistake" if saved == 1 else "mistakes"
                verb = "was" if saved == 1 else "were"
                label = _session_label(subject, module_name)
                suffix = f" ({label})" if label else ""
                print(f"  ℹ️  {saved} {noun} {verb} saved before aborting{suffix}.")
        else:
            # The session ended normally: state the subject, the module and how
            # many mistakes were added in this session. The full breakdown of
            # the mistake log lives in `cfa-prep mis`.
            noun = "mistake" if saved == 1 else "mistakes"
            label = _session_label(subject, module_name)
            suffix = f" for {label}" if label else ""
            print(f"\n✅ Session complete — {saved} {noun} saved{suffix}.")

    def _log_mcq(
        self,
        subject: str,
        module_name: str,
        level: str,
        show_hint: bool = True,
    ) -> str:
        """
        Log an L1 MCQ mistake with 3-option input.

        Every step of the question can be reached again: `\\b` goes one step
        back, `\\r` starts the question over and `\\q` leaves the session.

        Parameters:
            show_hint: print the navigation hint (only on the first entry)

        Returns one of:
            "finished" — user entered a blank question (stop the session)
            "skipped"  — question already logged, user chose not to re-add
            "quit"     — the user left the session
            "saved"    — a mistake was saved
        """
        if show_hint:
            print(f"\n  {HINT}")
        module_label = f" [{module_name}]" if module_name else ""
        tables: dict[str, Table | None] = {}

        def take_table(raw: str, previous: str) -> str:
            """Read the table that was pasted and show it as it will be shown."""
            if not raw.strip():
                if previous:
                    # The table of before is kept
                    print("  ↩️ Keeping the table from before.")
                    return previous
                tables["table"] = None
                return raw
            table = table_from_text(raw)
            tables["table"] = table
            if table:
                print("\n  📊 Table:")
                for row in render_table(table, indent="    "):
                    print(row)
                print()
            else:
                print("  (ignored — a table needs at least two columns)")
            return raw

        def check_question(value: str, previous: str) -> None:
            """The question text: an empty one ends the session."""
            if not value.strip():
                raise FinishSession
            if value != previous and not self._confirm_duplicate(value):
                raise SkipQuestion

        flow = StepFlow(self._prompt)
        steps = [
            Step(
                "question",
                f"Question text{module_label} (blank to finish): ",
                on_value=check_question,
            ),
            Step(
                "table",
                "  Paste the table below the question (press Enter if there is none):",
                kind="block",
                on_done=take_table,
                keep_on_empty=True,
            ),
            Step("option_a", "  Enter the 3 answer options:\n    A: "),
            Step("option_b", "    B: "),
            Step("option_c", "    C: "),
            Step("user_letter", "\nYour wrong answer (A/B/C, blank to skip): "),
            Step("correct_letter", "Correct answer (A/B/C): "),
            Step("explanation", "Explanation (optional): ", keep_on_empty=True),
        ]
        try:
            data = flow.run(steps)
        except FinishSession:
            return "finished"
        except SkipQuestion:
            print("  ⏭️ Skipped — already logged.")
            return "skipped"
        except QuitSession:
            return "quit"

        question = data["question"]
        option_a, option_b, option_c = data["option_a"], data["option_b"], data["option_c"]
        user_letter = data["user_letter"].upper()
        correct_letter = data["correct_letter"].upper()

        # Map letters to option text so the machine can identify the answer
        # regardless of display order (quiz can shuffle options later).
        letter_to_text = {"A": option_a, "B": option_b, "C": option_c}
        user_answer = letter_to_text.get(user_letter, user_letter)
        correct_answer = letter_to_text.get(correct_letter, correct_letter)

        explanation = data["explanation"]

        filepath = self.add_mistake(
            subject=subject,
            question=question,
            options=[option_a, option_b, option_c],
            user_answer=user_answer,
            correct_answer=correct_answer,
            explanation=explanation,
            module_name=module_name,
            level=level,
            table=tables.get("table"),
        )
        print(f"\n✅ Mistake saved to: {filepath}")
        return "saved"

    def _log_freeform(self, subject: str, module_name: str, level: str = "L1") -> bool:
        """
        Log an L2/L3 free-form mistake.

        Every step of the question can be reached again: `\\b` goes one step
        back, `\\r` starts the question over and `\\q` leaves the session.
        Returns True if a mistake was saved.
        """
        print(f"\n  {HINT}")
        tables: dict[str, Table | None] = {}

        def take_table(raw: str, previous: str) -> str:
            """Read the table that was pasted and show it as it will be shown."""
            if not raw.strip():
                if previous:
                    # The table of before is kept
                    print("  ↩️ Keeping the table from before.")
                    return previous
                tables["table"] = None
                return raw
            table = table_from_text(raw)
            tables["table"] = table
            if table:
                print("\n  📊 Table:")
                for row in render_table(table, indent="    "):
                    print(row)
                print()
            else:
                print("  (ignored — a table needs at least two columns)")
            return raw

        def check_question(value: str, previous: str) -> None:
            """The question text: an empty one cancels, a known one starts over."""
            if not value.strip():
                raise FinishSession
            if value != previous and not self._confirm_duplicate(value):
                print("  ⏭️ Skipped — already logged. Enter a different question.")
                raise RestartQuestion

        flow = StepFlow(self._prompt)
        steps = [
            Step(
                "question",
                "Enter the question description (enter a blank line to finish):",
                kind="block",
                on_value=check_question,
            ),
            Step(
                "table",
                "  Paste the table below the question (press Enter if there is none):",
                kind="block",
                on_done=take_table,
                keep_on_empty=True,
            ),
            Step("user_answer", "\nYour wrong answer (optional — blank to skip): "),
            Step("correct_answer", "Correct answer: "),
            Step("explanation", "Explanation (one-sentence summary): ", keep_on_empty=True),
        ]
        try:
            data = flow.run(steps)
        except FinishSession:
            print("  Cancelled.")
            return False
        except QuitSession:
            return False

        filepath = self.add_mistake(
            subject=subject,
            question=data["question"],
            user_answer=data["user_answer"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            module_name=module_name,
            level=level,
            table=tables.get("table"),
        )
        print(f"\n✅ Mistake saved to: {filepath}")
        return True

    def _pick_subject_and_module(
        self, curriculum: Curriculum, level: str
    ) -> tuple[str, str]:
        """
        Browse the curriculum to pick a subject and module.

        `\\b` goes back to the list before, `\\q` leaves the picker.  Returns
        (subject, module_name) or ("", "") if the user aborts.
        """
        subjects = curriculum.all_subjects(level)
        if not subjects:
            print("Curriculum is empty. Use free-text subject entry instead.")
            return "", ""

        while True:
            # 1. Pick subject
            print("\nPick a subject:")
            for i, s in enumerate(subjects, 1):
                print(f"  [{i}] {s}")
            choice = self._prompt("  > ").strip()
            if choice == QUIT:
                return "", ""
            if choice == BACK:
                print("  ⚠️ Already at the first step.")
                continue
            if not choice.isdigit():
                return "", ""
            idx = int(choice) - 1
            if idx < 0 or idx >= len(subjects):
                print("  (no such subject)")
                continue
            subject = subjects[idx]

            # 2. Pick module
            modules = curriculum.all_modules(level, subject)
            if not modules:
                print(f"No modules in {subject}.")
                return subject, ""

            while True:
                print(f"\n  {subject} — pick a module:")
                for i, m in enumerate(modules, 1):
                    print(f"    [{i}] {m}")
                choice = self._prompt("    > ").strip()
                if choice == QUIT:
                    return "", ""
                if choice == BACK:
                    # Back to the list of subjects
                    print("  ⬅️ Back to: subject")
                    break
                if not choice.isdigit():
                    return subject, ""
                idx = int(choice) - 1
                if idx < 0 or idx >= len(modules):
                    print("  (no such module)")
                    continue
                return subject, modules[idx]

    def get_recent_mistakes(self, limit: int = 10) -> list[MistakeRecord]:
        """
        Get the most recent N mistake records.
        Sorted by date in descending order.
        """
        return self.store.load_recent(limit)

    def all_mistakes(self) -> list[MistakeRecord]:
        """Return every mistake record, as stored."""
        return self.store.load_all()

    def _mistake_groups(self) -> dict[str, dict[str, int]]:
        """
        The number of logged questions per subject and per module.

        The counts come from the database, so the log does not have to be
        loaded to know which subjects and modules hold mistakes.
        """
        groups: dict[str, dict[str, int]] = {}
        for subject, module, questions, _attempts in self.store.grouped_counts():
            _ = groups.setdefault(subject, {})
            if module:
                groups[subject][module] = groups[subject].get(module, 0) + questions
        return groups

    def _module_records(self, subject: str, module: str) -> list[MistakeRecord]:
        """Return the questions of one module, as stored."""
        return self.store.load_by_subject_module(subject, module)

    @staticmethod
    def _option_letter(options: list[str], text: str) -> str:
        """Return the letter of the option with that text, or the text itself."""
        for letter, option in zip("ABC", options):
            if option == text:
                return letter
        return text

    def print_mistake(self, record: MistakeRecord, show_wrong: bool = True) -> None:
        """
        Print one mistake with everything it holds: the question, its table, the
        options, the answer and the explanation.

        The answer is named on its own line ("Answer: B"), so the options stay
        clean.  With show_wrong=False the answer that was chosen is left out,
        so the browse view does not point at the old mistake.
        """
        rule = "─" * 60
        subject = record.get("subject", "")
        module = record.get("module", "")
        location = f"{subject} | {module}" if subject and module else (subject or module)
        attempts = record.get("attempts", 1)
        date = record.get("date", "")
        if attempts > 1:
            # The question was logged again: the first date and the last one
            date = f"{date} (last {record.get('last_date', '')}, {attempts} attempts)"
        print(rule)
        print(f"  📅 {date}  |  {location}  |  {record.get('level', '')}")
        print()
        print(f"  {record.get('question', '')}")
        table = record.get("table")
        if table:
            print()
            for row in render_table(table, indent="  "):
                print(row)
        options = record.get("options") or []
        correct = record.get("correct_answer", "")
        history = list(record.get("wrong_answers") or [])
        if options:
            print()
            for letter, opt in zip("ABC", options):
                print(f"    {letter}. {opt}")
            print(f"\n    Answer: {self._option_letter(options, correct)}")
            if show_wrong:
                wrong = record.get("user_answer", "")
                print(f"    Your answer: {self._option_letter(options, wrong)}")
        else:
            print(f"\n    Answer: {correct}")
            if show_wrong:
                print(f"    Your answer: {record.get('user_answer', '')}")
        if show_wrong and len(history) > 1:
            # The answers that were given wrong before, so the pattern shows
            print(f"    Wrong answers so far: {', '.join(history)}")
        if record.get("explanation"):
            print(f"\n  💡 {record['explanation']}")
        print(rule)

    def browse_mistakes(self) -> None:
        """
        Show the logged mistakes of one module, chosen by subject and module.

        The subjects and the modules that have mistakes are offered in curriculum
        order, each with the number of questions it holds; every question of the
        chosen module is then shown in full.
        """
        try:
            self._browse_mistakes()
        except (KeyboardInterrupt, EOFError):
            print("\n  (cancelled)")

    def _browse_mistakes(self) -> None:
        """The picker of browse_mistakes, separated so Ctrl+C can be caught."""
        groups = self._mistake_groups()
        if not groups:
            print("\n  No mistakes logged yet.")
            return

        subject_rank, module_rank = self._curriculum_order()
        subjects = sorted(
            groups.keys(),
            key=lambda subject: (subject_rank.get(subject, len(subject_rank)), subject),
        )

        print("\n  Subject:")
        for i, subject in enumerate(subjects, 1):
            count = sum(groups[subject].values())
            print(f"    [{i}] {subject} ({count})")
        choice = self._prompt("    > ").strip()
        if not choice.isdigit():
            return
        index = int(choice) - 1
        if index < 0 or index >= len(subjects):
            print("  (no such subject)")
            return
        subject = subjects[index]

        modules = groups[subject]
        ranks = module_rank.get(subject, {})
        module_names = sorted(
            modules.keys(),
            key=lambda module: (ranks.get(module, len(ranks)), module),
        )
        print("\n  Module:")
        for i, module in enumerate(module_names, 1):
            print(f"    [{i}] {module} ({modules[module]})")
        choice = self._prompt("    > ").strip()
        if not choice.isdigit():
            return
        index = int(choice) - 1
        if index < 0 or index >= len(module_names):
            print("  (no such module)")
            return
        module = module_names[index]

        # Only the questions of the chosen module are loaded
        self.print_module_mistakes(subject, module)

    def print_module_mistakes(self, subject: str, module: str) -> None:
        """
        Print every question of one module that is logged as a mistake.

        This is the view of the mistake browser: the questions of a module, one
        after the other. Only the correct answer is marked.
        """
        records = self._module_records(subject, module)
        if not records:
            print(f"\n  No questions are logged in {subject} | {module}.")
            return
        attempts = sum(r.get("attempts", 1) for r in records)
        header = f"📝 {len(records)} in {subject} | {module}"
        if attempts > len(records):
            header += f" ({attempts} attempts)"
        print(f"\n  {header}\n")
        for record in records:
            # While browsing, only the correct answer is marked: the point is
            # to read the question again, not to look at the old mistake.
            self.print_mistake(record, show_wrong=False)
            print()

    def print_mistake_breakdown(self) -> None:
        """
        Print the mistake log grouped by subject and module, in curriculum order.

        A mistake belongs to a module, and the module is what the quiz reviews,
        so this is the breakdown that says what is still weak.  The curriculum is
        the source of truth for the order of the exam, so the summary follows it:
        the subjects in curriculum order, and inside a subject the modules in
        curriculum order.  This is the full summary shown by `cfa-prep mis`.
        """
        stats = self.get_mistake_stats()
        total_value = stats.get("total")
        total = total_value if isinstance(total_value, int) else 0
        modules_value = stats.get("modules")
        modules = (
            cast(dict[str, int], modules_value)
            if isinstance(modules_value, dict)
            else {}
        )
        if not modules:
            return
        noun = "mistake" if total == 1 else "mistakes"
        attempts_value = stats.get("attempts")
        attempts = attempts_value if isinstance(attempts_value, int) else total
        title = f"Mistake log by subject and module ({total} {noun})"
        if attempts > total:
            title += f", {attempts} attempts"
        print_section(title)
        module_attempts_value = stats.get("module_attempts")
        module_attempts = (
            cast(dict[str, int], module_attempts_value)
            if isinstance(module_attempts_value, dict)
            else {}
        )
        subject_rank, module_rank = self._curriculum_order()
        ordered = sorted(
            modules.items(),
            key=lambda item: self._group_key(item[0], subject_rank, module_rank),
        )
        width = max(len(str(count)) for _group, count in ordered)
        for group, count in ordered:
            # The questions that were answered wrong again are counted apart
            group_attempts = module_attempts.get(group, count)
            suffix = f" ({group_attempts} attempts)" if group_attempts > count else ""
            print(f"  {count:>{width}} | {group}{suffix}")

    @staticmethod
    def _curriculum_order() -> tuple[dict[str, int], dict[str, dict[str, int]]]:
        """
        Return the curriculum position of every subject and module.

        The first value maps a subject to its rank, the second maps a subject to
        the rank of its modules.  A subject or module that is not part of the
        curriculum has no rank and ends up at the end of the list.
        """
        data = Curriculum().load()
        subject_rank: dict[str, int] = {}
        module_rank: dict[str, dict[str, int]] = {}
        for level in sorted(data.keys()):
            for subject, modules in data[level].items():
                if subject not in subject_rank:
                    subject_rank[subject] = len(subject_rank)
                    module_rank[subject] = {}
                ranks = module_rank[subject]
                for module in modules:
                    if module not in ranks:
                        ranks[module] = len(ranks)
        return subject_rank, module_rank

    @staticmethod
    def _group_key(
        group: str,
        subject_rank: dict[str, int],
        module_rank: dict[str, dict[str, int]],
    ) -> tuple[int, int, str]:
        """
        Return the sort key of a "Subject > Module" group in curriculum order.

        Groups that the curriculum does not know are sorted last, alphabetically.
        """
        subject, _, module = group.partition(" > ")
        subject_key = subject_rank.get(subject, len(subject_rank))
        ranks = module_rank.get(subject, {})
        module_key = ranks.get(module, len(ranks))
        return (subject_key, module_key, group)

    def get_mistake_stats(self) -> dict[str, object]:
        """
        Get mistake statistics.
        Returns the total count, per-subject counts, and per-module counts.
        The attempts are counted as well: a question that was logged again is
        one mistake, but several attempts.
        """
        groups = self.store.grouped_counts()
        total = sum(questions for _s, _m, questions, _a in groups)
        attempts = sum(tries for _s, _m, _q, tries in groups)
        if total == 0:
            return {
                "total": 0,
                "attempts": 0,
                "subjects": {},
                "modules": {},
                "module_attempts": {},
            }

        subj_count: dict[str, int] = {}
        module_count: dict[str, int] = {}
        module_attempts: dict[str, int] = {}
        for subject, module, questions, tries in groups:
            subj = subject or "Unknown"
            subj_count[subj] = subj_count.get(subj, 0) + questions
            if module:
                key = f"{subj} > {module}"
                module_count[key] = module_count.get(key, 0) + questions
                module_attempts[key] = module_attempts.get(key, 0) + tries

        return {
            "total": total,
            "attempts": attempts,
            "subjects": subj_count,
            "modules": module_count,
            "module_attempts": module_attempts,
        }

    def list_mistake_files(self) -> list[Path]:
        """List the mistakes data files that exist."""
        files: list[Path] = []
        if self.db_file.exists():
            files.append(self.db_file)
        return files

    def export_mistakes(self, path: Path) -> Path:
        """Write the log as a JSON file, the format that can be read by hand."""
        self.store.export_json(path)
        return path

    def merge_duplicates(self) -> int:
        """
        Merge the questions that are logged twice into a single row.

        A question that was logged twice under a slightly different text (a
        trailing colon) ended up in two rows.  The extra rows are removed and
        their attempts are folded into the row that is kept.
        """
        return self.store.merge_duplicates()

    def undo_last(self) -> MistakeRecord | None:
        """
        Remove the question that was logged last.

        It is the way back when a mistake was saved by accident: the question
        that is removed is returned, so it can be shown.
        """
        record = self.store.latest()
        if record is None:
            return None
        _ = self.store.delete(record["question_id"])
        return record

    def check_duplicates(self) -> list[list[MistakeRecord]]:
        """
        Return the questions that are logged more than once, with their records.

        Every group holds the records of one question that was logged twice: the
        first one is the row that would be kept, the other ones are the rows
        that would be merged into it.
        """
        return self.store.duplicate_groups()
