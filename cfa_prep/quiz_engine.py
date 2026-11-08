# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Quiz engine module
Author: CodeBuddy AI Assistant
Purpose: Provide quiz modes for the three CFA exam levels (L1/L2/L3),
         with random question selection and mistake-priority strategy, interactive answering, and instant scoring.
"""

import random
from typing import TypedDict

from .mistake_analyzer import MistakeAnalyzer
from .progress_tracker import ProgressTracker
from .curriculum import Curriculum
from .quiz_stats import (
    RESULT_CORRECT,
    RESULT_SKIPPED,
    RESULT_WRONG,
    SOURCE_MISTAKE,
    QuizStats,
    describe,
    topic_of,
)


def read_input(prompt: str = "") -> str:
    """
    Read a line of user input.

    Strips surrounding whitespace and a leading UTF-8 BOM, which Windows shells
    (e.g. PowerShell) prepend to piped input and which would otherwise make the
    first answer look invalid.
    """
    return input(prompt).strip().lstrip("\ufeff").strip()


class MistakeQuestion(TypedDict):
    """A logged L1 MCQ mistake, replayable as a quiz question."""
    subject: str
    module: str
    key_point: str
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

    def _get_mistake_topics(self) -> list[str]:
        """Extract knowledge points from the mistake log for priority question selection"""
        records = self.mistake_analyzer.get_recent_mistakes(limit=20)
        topics: list[str] = []
        for r in records:
            kp = r.get("key_point", "")
            if kp:
                topics.append(kp)
        return topics

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
                    key_point=str(r.get("key_point", "")),
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
        print(f"  Topic: {item.get('key_point', '')}")
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
                    topic=self._topic_label(item),
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
                topic=self._topic_label(item),
                level="L1",
                source=SOURCE_MISTAKE,
            )
        return correct

    @staticmethod
    def _topic_label(item: MistakeQuestion) -> str:
        """Build a curriculum-style label for a mistake item."""
        subject = item.get("subject", "")
        module = item.get("module", "")
        key_point = item.get("key_point", "")
        if subject and module:
            return f"[{subject} > {module}] {key_point}"
        return key_point or subject

    def _auto_log_mistake(self, item: MistakeQuestion) -> None:
        """Re-log a mistake that was answered incorrectly during review."""
        _ = self.mistake_analyzer.add_mistake(
            subject=item["subject"],
            question=item["question"],
            user_answer="",
            correct_answer=item["correct"],
            key_point=item["key_point"],
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

    def _boost_set(self, all_topics: list[str], raw_topics: list[str]) -> set[str]:
        """
        Map plain topic / key-point strings onto their curriculum labels so the
        mistake log and the fuzzy list can boost the matching quiz topics.
        """
        by_text: dict[str, str] = {}
        for label in all_topics:
            _ = by_text.setdefault(topic_of(label).strip().lower(), label)

        boosts: set[str] = set()
        for raw in raw_topics:
            key = raw.strip().lower()
            if not key:
                continue
            boosts.add(by_text.get(key, raw))
        return boosts

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

        priority_pool = self._boost_set(
            all_topics, self._get_mistake_topics() + self._get_fuzzy_topics()
        )
        return self.stats.select_topics(all_topics, 10, boosted=priority_pool)

    def _subject_from_label(self, label: str) -> str:
        """
        Extract the subject name from a curriculum topic label of the form
        "[Subject > Module] Topic". Returns the subject portion, or "" if unparseable.
        """
        bracket = label.find("]")
        if bracket == -1:
            return ""
        inner = label[1:bracket]
        # Inner is "Subject > Module"; subject is the part before the module separator.
        if ">" in inner:
            return inner.split(">", 1)[0].strip()
        return inner.strip()

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
        priority_topics = list(set(self._get_mistake_topics() + self._get_fuzzy_topics()))

        # Choose the vignette topic
        if priority_topics and random.random() < 0.4:
            vignette_topic = random.choice(priority_topics)
        else:
            vignette_topic = random.choice(all_topics)

        # Generate 3 related questions (selected from the relevant subject's modules)
        subject = self._subject_from_label(vignette_topic)
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
            self.stats.record_topic_result(topic, outcome, ref=ref, level=level)
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
            self.stats.record_topic_result(q, outcome, level=level)
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
        self.stats.record_topic_result(topic, RESULT_SKIPPED, level=level)

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
