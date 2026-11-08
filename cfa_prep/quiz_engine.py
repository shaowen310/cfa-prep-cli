# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Quiz engine module
Author: CodeBuddy AI Assistant
Purpose: Provide quiz modes for the three CFA exam levels (L1/L2/L3),
         with random question selection and mistake-priority strategy, interactive answering, and instant scoring.
"""

import random
from typing import TypedDict

from .mistake_analyzer import MistakeAnalyzer, question_id
from .progress_tracker import ProgressTracker
from .curriculum import (
    Curriculum,
    module_group,
    module_group_of,
    subject_of,
)
from .quiz_stats import (
    RESULT_CORRECT,
    RESULT_SKIPPED,
    RESULT_WRONG,
    QuizStats,
    describe,
)

# Where a recorded question came from.
SOURCE_MISTAKE = "mistake"   # a logged mistake, replayed from the mistake log
SOURCE_TOPIC = "topic"       # a curriculum question answered from the book
SOURCE_BOOK = "book"         # a curriculum question with a book reference

BOOST_AMOUNT = 1.5    # extra priority for topics in the mistake/fuzzy lists


def read_input(prompt: str = "") -> str:
    """
    Read a line of user input.

    Strips surrounding whitespace and a leading UTF-8 BOM, which Windows shells
    (e.g. PowerShell) prepend to piped input and which would otherwise make the
    first answer look invalid.
    """
    return input(prompt).strip().lstrip("\ufeff").strip()


def curriculum_question_id(label: str, ref: str = "") -> str:
    """
    Return the stable id of a curriculum question.

    A curriculum question is answered from the book, so its identity is the
    curriculum topic it belongs to plus the optional book reference.  The
    curriculum is the source of truth for that identity - the statistics file
    only stores the id.
    """
    return question_id(f"{label}\n{ref}" if ref else label)


class MistakeQuestion(TypedDict):
    """A logged L1 MCQ mistake, replayable as a quiz question."""
    subject: str
    module: str
    question: str
    question_id: str
    options: list[str]
    correct: str


class QuizEngine:
    """
    CFA quiz engine.
    Generates different question types based on level (L1/L2/L3),
    using a mistake-priority (40%) + random selection (60%) strategy.
    """

    def __init__(self):
        self.mistake_analyzer: MistakeAnalyzer = MistakeAnalyzer()
        self.progress_tracker: ProgressTracker = ProgressTracker()
        self.curriculum: Curriculum = Curriculum()
        self.stats: QuizStats = QuizStats()
        self.score: int = 0
        self.total: int = 0
        self.correct: int = 0
        self.wrong: int = 0
        self.skipped: int = 0
        self.randomize: bool = True

    def _get_all_topics(self, level: str = "L1") -> list[str]:
        """
        Get all knowledge points across all subjects and modules for a level.
        Drawn from the imported curriculum; returns [] if the curriculum is empty.
        """
        return self.curriculum.all_topics(level.upper())

    def _get_mistake_modules(self) -> set[str]:
        """
        Return the modules the user has logged mistakes in.

        The module is the reliable link between a mistake and the curriculum:
        subject and module are curriculum values, while the topic a mistake
        could have been filed under is not recorded.
        """
        records = self.mistake_analyzer.get_recent_mistakes(limit=50)
        modules: set[str] = set()
        for r in records:
            subject = str(r.get("subject", ""))
            module = str(r.get("module", ""))
            if subject and module:
                modules.add(module_group(subject, module))
        return modules

    def _get_mistake_questions(self, limit: int = 10) -> list[MistakeQuestion]:
        """
        Fetch logged L1 MCQ mistakes that have full question/options data,
        so the quiz can replay them as real, checkable questions.
        """
        records = self.mistake_analyzer.get_recent_mistakes(limit=50)
        questions: list[MistakeQuestion] = []
        for r in records:
            options = r.get("options") or []
            correct = r.get("correct_answer", "")
            question = r.get("question", "")
            if len(options) >= 2 and question and correct:
                questions.append(MistakeQuestion(
                    subject=str(r.get("subject", "")),
                    module=str(r.get("module", "")),
                    question=question,
                    # The id is taken from the log, never derived again here.
                    question_id=str(r.get("question_id", "")),
                    options=[str(o) for o in options],
                    correct=str(correct),
                ))
            if len(questions) >= limit:
                break
        return questions

    def _run_mistake_mcq(self, item: MistakeQuestion) -> bool:
        """
        Replay a logged MCQ mistake with shuffled options and check the answer.
        Returns True if the user answered correctly, False otherwise.
        """
        correct_text = item["correct"]
        # The question id comes from the mistake log, which is the single
        # source of truth for it — it is never derived again here.
        qid = item.get("question_id", "")
        options = list(item["options"])
        # Shuffle so the correct answer is not always at the same position
        if self.randomize:
            random.shuffle(options)
        labels = "ABC"
        # A tuple, not the string: "" is a substring of "ABC", so an empty
        # answer would otherwise pass the membership test and count as "A".
        valid_answers = ("A", "B", "C")

        print(f"{'─' * 50}")
        print(f"  🔁 Mistake review")
        subject = item.get("subject", "")
        module = item.get("module", "")
        label = f"{subject} > {module}" if subject and module else subject or "Mistake"
        print(f"  Source: {label}")
        print(f"  Module: {item.get('module', '')}")
        print(f"{'─' * 50}")
        print(f"\n  {item['question']}")
        for i, opt in enumerate(options):
            print(f"    {labels[i]}. {opt}")

        answer = read_input("\nYour wrong answer (A/B/C): ").upper()
        if answer == "Q":
            print("👋 Quiz exited")
            raise KeyboardInterrupt

        if answer not in valid_answers:
            # No answer given: the question counts as skipped, never as wrong.
            print("⚠️ No answer given — recorded as skipped.")
            self.total += 1
            self.skipped += 1
            if qid:
                self.stats.record_question(
                    qid,
                    RESULT_SKIPPED,
                    question=item["question"],
                    level="L1",
                    source=SOURCE_MISTAKE,
                )
            return False

        chosen = options[labels.index(answer)]
        correct = chosen == correct_text
        self.total += 1
        if correct:
            print(f"\n  ✅ Correct! ({labels[labels.index(answer)]}. {chosen})")
            self.score += 1
            self.correct += 1
        else:
            correct_label = labels[options.index(correct_text)]
            print(f"\n  ❌ Incorrect. Correct answer: {correct_label}. {correct_text}")
            self.wrong += 1
            # Auto-log the repeated mistake
            self._auto_log_mistake(item)
        # Record the outcome against the question, so it is rescheduled
        if qid:
            self.stats.record_question(
                qid,
                RESULT_CORRECT if correct else RESULT_WRONG,
                question=item["question"],
                level="L1",
                source=SOURCE_MISTAKE,
            )
        return correct

    def _auto_log_mistake(self, item: MistakeQuestion) -> None:
        """Re-log a mistake that was answered incorrectly during review."""
        if not item.get("module"):
            # Without a module the copy cannot be attributed to the curriculum.
            return
        _ = self.mistake_analyzer.add_mistake(
            subject=item["subject"],
            question=item["question"],
            user_answer="",
            correct_answer=item["correct"],
            correct_conclusion="",
            module_name=item["module"],
            level="L1",
            options=item["options"],
            # The re-logged copy keeps the id of the original question, so both
            # records refer to the same question.
            existing_question_id=item.get("question_id", ""),
        )

    def _get_fuzzy_topics(self) -> list[str]:
        """Extract fuzzy knowledge points from progress tracking"""
        return self.progress_tracker.get_key_points_to_review()

    def _get_fuzzy_modules(self) -> set[str]:
        """The modules the user marked as fuzzy in the progress tracker."""
        modules: set[str] = set()
        for label in self._get_fuzzy_topics():
            if label.startswith("["):
                modules.add(module_group_of(label))
        return modules

    def _weak_module_topics(self, all_topics: list[str]) -> list[str]:
        """The curriculum topics of the modules the user is weak in."""
        weak = self._get_mistake_modules() | self._get_fuzzy_modules()
        return [label for label in all_topics if module_group_of(label) in weak]

    def _boost_set(self, all_topics: list[str]) -> set[str]:
        """
        Boost the curriculum topics of the modules the user is weak in.

        A mistake belongs to its module and a fuzzy point to its module too, so
        the boost follows the module - the level the user can trust.
        """
        weak_modules = self._get_mistake_modules() | self._get_fuzzy_modules()
        boosts: set[str] = set()
        for label in all_topics:
            if module_group_of(label) in weak_modules:
                boosts.add(label)
        return boosts

    def _topic_question_ids(self, all_topics: list[str]) -> dict[str, list[str]]:
        """
        Map every curriculum topic to the question ids that belong to it.

        A topic owns its own curriculum question.  A logged mistake belongs to
        the module it was logged in, so it counts for every topic of that
        module.  The mistake log is the source of truth for the ids of the
        mistakes, so they are read from there.
        """
        mapping: dict[str, list[str]] = {}
        by_module: dict[str, list[str]] = {}
        for label in all_topics:
            mapping[label] = [curriculum_question_id(label)]
            by_module.setdefault(module_group_of(label), []).append(label)

        for record in self.mistake_analyzer.get_recent_mistakes(limit=200):
            qid = str(record.get("question_id", ""))
            if not qid:
                continue
            subject = str(record.get("subject", ""))
            module = str(record.get("module", ""))
            if not subject or not module:
                continue
            for label in by_module.get(module_group(subject, module), []):
                mapping[label].append(qid)
        return mapping

    def _generate_l1_quiz(self, level: str = "L1") -> list[str]:
        """
        Generate L1 questions (10 mixed single-choice questions).
        The selection is driven by the stored statistics: topics that are long
        overdue, that were answered wrongly before, or that have never been
        tested get the highest priority, while topics answered correctly in a
        row are pushed further into the future.
        """
        all_topics = self._get_all_topics(level)
        if not all_topics:
            return []

        priority_pool = self._boost_set(all_topics)
        question_ids = self._topic_question_ids(all_topics)

        # A topic is as urgent as its most urgent question, so a single badly
        # known question lifts the whole topic, while a topic whose questions
        # are all mastered is pushed back.
        scored: list[tuple[float, str]] = []
        for topic in all_topics:
            ids = question_ids.get(topic) or [curriculum_question_id(topic)]
            score = max(self.stats.priority_of(qid) for qid in ids)
            if topic in priority_pool:
                score += BOOST_AMOUNT
            scored.append((score, topic))

        # At most two questions per module, so a weak module comes back often
        # without crowding out the rest of the curriculum.
        return self.stats.select_scored(
            scored, 10, group_of=module_group_of, limit_per_group=2
        )

    def _subject_topics(self, level: str, subject: str) -> list[str]:
        """Return all "[Subject > Module] Topic" labels for a subject, across its modules."""
        if not subject:
            return []
        all_topics = self._get_all_topics(level)
        return [t for t in all_topics if t.startswith(f"[{subject} >")]

    def _generate_l2_quiz(self, level: str = "L2") -> dict[str, list[str] | str]:
        """
        Generate L2 questions (1 vignette + 3 sub-questions).
        A vignette is a case scenario accompanied by 3 related questions.
        """
        all_topics = self._get_all_topics(level)
        priority_topics = self._weak_module_topics(all_topics)

        # Choose the vignette topic
        if priority_topics and random.random() < 0.4:
            vignette_topic = random.choice(priority_topics)
        else:
            vignette_topic = random.choice(all_topics)

        # Generate 3 related questions (selected from the relevant subject's modules)
        subject = subject_of(vignette_topic)
        related_topics = self._subject_topics(level, subject)
        if not related_topics:
            related_topics = [vignette_topic]

        sub_questions = random.sample(related_topics, min(3, len(related_topics)))
        while len(sub_questions) < 3:
            sub_questions.append(random.choice(all_topics))
        if self.randomize:
            random.shuffle(sub_questions)

        return {
            "vignette_topic": vignette_topic,
            "sub_questions": sub_questions,
            "format": "1 case scenario + 3 multiple-choice questions",
        }

    def _generate_l3_quiz(self) -> dict[str, str]:
        """
        Generate L3 questions (1 IPS scenario or behavioral finance scenario + essay questions).
        """
        scenario_types = ["IPS construction (personal)", "IPS construction (institutional)", "Behavioral finance bias analysis", "Asset allocation decision"]
        scenario = random.choice(scenario_types)

        return {
            "scenario": scenario,
            "format": "1 scenario analysis + essay question",
            "instructions": "Based on the scenario, write your analysis process and recommendation (suggest 18 minutes)",
        }

    def start_quiz(self, level: str = "L1", randomize: bool = True) -> None:
        """
        Start the quiz.

        Parameters:
            level: exam level (L1, L2, L3)
            randomize: whether to randomize question order and answer options
        """
        level = level.upper()
        self.randomize = randomize
        self.score = 0
        self.total = 0
        self.correct = 0
        self.wrong = 0
        self.skipped = 0

        # Batch the statistics writes: the file is rewritten in full each time,
        # so it is written once at the end instead of once per answer.
        self.stats = QuizStats(autosave=False)

        print("\n" + "=" * 60)
        print(f"  📝 CFA {level} Quiz Mode")
        print("=" * 60)

        try:
            if level == "L1":
                self._do_l1_quiz(level)
            elif level == "L2":
                self._do_l2_quiz(level)
            elif level == "L3":
                self._do_l3_quiz()
            else:
                print(f"❌ Unsupported level: {level}, please use L1/L2/L3")
        finally:
            self.stats.flush()

    def _do_l1_quiz(self, level: str = "L1") -> None:
        """Run the L1 quiz flow"""
        # First replay logged mistakes as real MCQ questions
        mistake_questions = self._get_mistake_questions()
        if self.randomize:
            random.shuffle(mistake_questions)
        if mistake_questions:
            print(f"\n🔁 {len(mistake_questions)} mistake review question(s) first\n")
            for item in mistake_questions:
                try:
                    _ = self._run_mistake_mcq(item)
                except KeyboardInterrupt:
                    print("👋 Quiz exited")
                    self._show_quiz_summary(level)
                    return

        # Then run the regular topic questions
        topics = self._generate_l1_quiz(level)
        print(f"\n📋 {len(topics)} regular questions")
        print("Answer each question based on the knowledge point; your responses will be recorded.\n")

        for i, topic in enumerate(topics, 1):
            print(f"{'─' * 50}")
            print(f"  📌 Question {i}/{len(topics)}")
            print(f"  Topic: {topic}")
            print(f"{'─' * 50}")

            # Generate the question prompt
            self._generate_question_prompt(topic)

            # User answer
            print("\nPlease choose an answer, or type the book question reference")
            print("(e.g. 'Q12') to track this question on its own; 's' skips, 'q' quits:")
            print("  [A] [B] [C] [D]")
            raw = read_input("Your choice: ").strip()
            answer = raw.upper()
            ref = ""

            if len(raw) == 1:
                if answer == "Q":
                    print("👋 Quiz exited")
                    break
                elif answer == "S":
                    print(f"⏭️ Skipped question {i}")
                    self._record_skipped(topic, level)
                    continue
                elif answer not in ("A", "B", "C", "D"):
                    print("⚠️ No answer given — recorded as skipped.")
                    self._record_skipped(topic, level)
                    continue
            elif raw:
                # A free-form answer is read as the book question reference, so
                # two different questions of the same topic are tracked apart.
                ref = raw
                print(f"  🔖 Reference: {ref}")
            else:
                print("⚠️ No answer given — recorded as skipped.")
                self._record_skipped(topic, level)
                continue

            self.total += 1
            if not ref:
                print(f"\n  ✅ Answer recorded: {answer}")
            outcome = self._ask_outcome()
            if outcome == RESULT_CORRECT:
                self.score += 1
                self.correct += 1
            elif outcome == RESULT_WRONG:
                self.wrong += 1
            else:
                self.skipped += 1
            self.stats.record_question(
                curriculum_question_id(topic, ref),
                outcome,
                question=topic,
                level=level,
                source=SOURCE_BOOK if ref else SOURCE_TOPIC,
            )
            print(f"  💡 For any mistake, log it with the 'mistake -a' command.")

        self._show_quiz_summary(level)

    def _do_l2_quiz(self, level: str = "L2") -> None:
        """Run the L2 quiz flow"""
        quiz = self._generate_l2_quiz(level)
        print(f"\n📋 Case topic: {quiz['vignette_topic']}")
        print(f"📋 Format: {quiz['format']}")
        print("\nPlease read the following case scenario (get the full vignette from the official curriculum):")
        print(f"  Topic: {quiz['vignette_topic']}")
        print(f"  Sub-questions:")
        for i, q in enumerate(quiz["sub_questions"], 1):
            print(f"    {i}. {q}")

        self.total = 0
        print("\nPlease answer each question (or enter 'q' to quit):")
        for i, q in enumerate(quiz["sub_questions"], 1):
            print(f"\n{'─' * 50}")
            print(f"  📌 Sub-question {i}/3: {q}")
            print(f"{'─' * 50}")
            answer = read_input("Your answer (A/B/C): ").strip().upper()
            if answer == "Q":
                print("👋 Quiz exited")
                break
            if answer not in ("A", "B", "C", "D"):
                # No answer given: the question counts as skipped, never as wrong.
                print("⚠️ No answer given — recorded as skipped.")
                self._record_skipped(q, level)
                continue
            print(f"  ✅ Answer recorded: {answer}")
            outcome = self._ask_outcome()
            if outcome == RESULT_CORRECT:
                self.score += 1
                self.correct += 1
            elif outcome == RESULT_WRONG:
                self.wrong += 1
            else:
                self.skipped += 1
            self.total += 1
            self.stats.record_question(
                curriculum_question_id(q),
                outcome,
                question=q,
                level=level,
                source=SOURCE_TOPIC,
            )
            print(f"  💡 Check against the standard answer.")

        self._show_quiz_summary(level)

    def _do_l3_quiz(self) -> None:
        """Run the L3 quiz flow"""
        quiz = self._generate_l3_quiz()
        print(f"\n📋 Scenario type: {quiz['scenario']}")
        print(f"📋 Format: {quiz['format']}")
        print(f"📋 {quiz['instructions']}")
        print(f"\nWrite your analysis below (enter a blank line to finish):\n")

        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)

        self.total = 1
        self.score = 1  # Placeholder
        print("\n  ✅ Your response has been recorded.")
        print("  💡 Self-assess against the standard answer; if improvement is needed, use 'mistake -a' to log weak points.")

        self._show_quiz_summary("L3")

    def _generate_question_prompt(self, topic: str) -> None:
        """
        Generate a question prompt based on the knowledge point.
        In practice, users should select the corresponding question from a question bank.

        Parameters:
            topic: knowledge point description
        """
        # Provide direction hints for the question
        print(f"\n  📖 Please select a question related to「{topic}」from the question bank for practice.")
        print(f"  We recommend using end-of-chapter questions from the official curriculum or QBank questions on this topic.")

    def _record_skipped(self, topic: str, level: str) -> None:
        """
        Record a question the user did not answer as skipped.

        A question without an answer is never counted as wrong: it stays due
        and keeps some priority, but it does not lower the ease or count as a
        mistake.
        """
        self.total += 1
        self.skipped += 1
        self.stats.record_question(
            curriculum_question_id(topic),
            RESULT_SKIPPED,
            question=topic,
            level=level,
            source=SOURCE_TOPIC,
        )

    def _ask_outcome(self) -> str:
        """
        Ask the user to self-assess the answer.

        The CLI has no question bank, so the user picks their answer from the
        book and then confirms whether it was right. The outcome drives the
        statistics and the rescheduling of the topic.

        An empty answer means the user did not assess the question at all, so
        it is recorded as skipped rather than as a wrong answer.
        """
        while True:
            print("  Did you answer correctly? [y]es / [n]o / [s]kip:")
            choice = read_input("  > ").strip().lower()
            if choice in ("y", "yes"):
                return RESULT_CORRECT
            if choice in ("n", "no"):
                return RESULT_WRONG
            if choice in ("s", "skip"):
                return RESULT_SKIPPED
            if not choice:
                print("  ⚠️ No answer given — recorded as skipped.")
                return RESULT_SKIPPED
            print("  ⚠️ Please choose y, n or s.")

    def _show_quiz_summary(self, level: str = "L1") -> None:
        """Show the quiz summary, persist the session and report the statistics."""
        if self.total == 0:
            print("\n📊 No questions completed this time.")
            return

        accuracy = (self.correct / self.total * 100) if self.total else 0.0

        print(f"\n{'=' * 50}")
        print(f"  📊 Quiz Summary")
        print(f"{'=' * 50}")
        print(f"  Level: {level}")
        print(f"  Questions completed: {self.total}")
        print(f"  ✅ Correct: {self.correct}")
        print(f"  ❌ Wrong: {self.wrong}")
        print(f"  ⏭️  Skipped: {self.skipped}")
        print(f"  🎯 Accuracy: {accuracy:.1f}%")

        # Persist the session so the history stays complete, then write the
        # batched statistics to disk in one go.
        self.stats.record_session(level, self.total, self.correct, self.wrong, self.skipped)
        self.stats.flush()
        print(f"  📈 Saved to: {self.stats.stats_file}")

        weakest = self.stats.weakest_questions(limit=3)
        if weakest:
            print(f"\n  🔁 Questions to review next (most wrong answers):")
            for _key, stat in weakest:
                print(
                    f"     • {describe(stat)}"
                    f" ({stat['times_wrong']} wrong / {stat['times_seen']} seen)"
                )

        due = self.stats.due_questions(limit=3)
        if due:
            print(f"\n  📅 Due for review:")
            for _key, stat, overdue in due:
                when = "overdue" if overdue > 0 else "due today"
                print(f"     • {describe(stat)} ({when})")

        print(f"  📝 For any mistakes, log them with the following command:")
        print(f"     cfa-prep mistake -a")
        print(f"  📊 View progress:")
        print(f"     cfa-prep recap")
        print(f"  📊 View quiz statistics:")
        print(f"     cfa-prep stats")
