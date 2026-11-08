# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Quiz engine module
Author: CodeBuddy AI Assistant
Purpose: Provide quiz modes for the three CFA exam levels (L1/L2/L3),
         with random topic selection driven by the logged mistakes, replay of
         those mistakes as real multiple-choice questions, and instant scoring.
"""

import random
from typing import TypedDict

from .mistake_analyzer import MistakeAnalyzer
from .progress_tracker import ProgressTracker
from .curriculum import (
    Curriculum,
    module_group,
    module_group_of,
    subject_of,
    topic_of,
)
from .quiz_stats import (
    RESULT_CORRECT,
    RESULT_SKIPPED,
    RESULT_WRONG,
    UNSEEN_PRIORITY,
    QuizStats,
    describe,
)

BOOST_AMOUNT = 1.5    # extra priority for topics in the mistake/fuzzy lists


def read_input(prompt: str = "") -> str:
    """
    Read a line of user input.

    Strips surrounding whitespace and a leading UTF-8 BOM, which Windows shells
    (e.g. PowerShell) prepend to piped input and which would otherwise make the
    first answer look invalid.

    An end of input (piped input that ran out, or Ctrl+D) is an empty answer
    rather than an error: the caller decides what an empty answer means.
    """
    try:
        return input(prompt).strip().lstrip("\ufeff").strip()
    except EOFError:
        return ""


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

    def _module_scores(self) -> dict[str, float]:
        """
        Score every module by the mistakes logged in it.

        A module is as urgent as its most urgent mistake; a module without any
        mistake counts as unseen.  The modules the user marked as fuzzy are
        treated like a weak module.

        The score belongs to the module, so every topic of that module inherits
        it - a topic is not tracked on its own, it only carries its module.
        """
        scores: dict[str, float] = {}
        weak: set[str] = set()

        for record in self.mistake_analyzer.get_recent_mistakes(limit=200):
            subject = str(record.get("subject", ""))
            module = str(record.get("module", ""))
            qid = str(record.get("question_id", ""))
            if not subject or not module or not qid:
                continue
            group = module_group(subject, module)
            weak.add(group)
            scores[group] = max(scores.get(group, 0.0), self.stats.priority_of(qid))

        weak.update(self._get_fuzzy_modules())

        for group in weak:
            scores[group] = scores.get(group, UNSEEN_PRIORITY) + BOOST_AMOUNT

        return scores

    def _module_topics(self, level: str = "L1") -> dict[str, list[str]]:
        """
        Return the curriculum topics of every module.

        The topics are the material to cover, not a queue of items: nothing is
        tracked per topic, the module is the unit that comes back until you log
        fewer mistakes in it.
        """
        by_module: dict[str, list[str]] = {}
        for label in self._get_all_topics(level):
            by_module.setdefault(module_group_of(label), []).append(label)
        return by_module

    def _get_mistake_questions(
        self, limit: int = 10, limit_per_module: int = 2
    ) -> list[MistakeQuestion]:
        """
        Fetch logged L1 MCQ mistakes that have full question/options data,
        so the quiz can replay them as real, checkable questions.

        At most `limit_per_module` questions of one module are selected, so a
        single weak module cannot take over the review.  The questions that are
        still replayable are ordered by their urgency in the statistics, so the
        ones that are due or repeatedly wrong come first.
        """
        records = self.mistake_analyzer.get_recent_mistakes(limit=50)
        candidates: list[tuple[float, MistakeQuestion]] = []
        for r in records:
            options = r.get("options") or []
            correct = r.get("correct_answer", "")
            question = r.get("question", "")
            if len(options) >= 2 and question and correct:
                # The id is taken from the log, never derived again here.
                qid = str(r.get("question_id", ""))
                candidates.append((
                    self.stats.priority_of(qid),
                    MistakeQuestion(
                        subject=str(r.get("subject", "")),
                        module=str(r.get("module", "")),
                        question=question,
                        question_id=qid,
                        options=[str(o) for o in options],
                        correct=str(correct),
                    ),
                ))

        # Most urgent first; equally urgent questions keep their order in the log.
        candidates.sort(key=lambda pair: -pair[0])

        selected: list[MistakeQuestion] = []
        taken: dict[str, int] = {}
        for _score, item in candidates:
            if len(selected) >= limit:
                break
            group = self._module_group_of(item)
            if taken.get(group, 0) >= limit_per_module:
                continue
            taken[group] = taken.get(group, 0) + 1
            selected.append(item)
        return selected

    @staticmethod
    def _module_group_of(item: MistakeQuestion) -> str:
        """
        Return the module group of a mistake.

        A mistake always belongs to a module, so the group is the module it was
        logged in.  A mistake without a module belongs to no module and is
        therefore not counted against the per-module limit.
        """
        subject = str(item.get("subject", ""))
        module = str(item.get("module", ""))
        if not module:
            return f"?{item.get('question_id', '')}"
        return module_group(subject, module)

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
        print(f"  Module: {label}")
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
        weak = set(self._module_scores())
        return [label for label in all_topics if module_group_of(label) in weak]

    def _modules_of(self, items: list[MistakeQuestion]) -> list[str]:
        """
        Return the modules the given mistake questions belong to, in order.

        The modules are the unit the quiz reviews: a mistake belongs to a module
        and the module carries the score.
        """
        modules: list[str] = []
        for item in items:
            group = self._module_group_of(item)
            if group not in modules:
                modules.append(group)
        return modules

    def _unseen_modules(self, level: str = "L1") -> list[str]:
        """The modules the user has not logged a mistake in yet."""
        scored = set(self._module_scores())
        return [group for group in self._module_topics(level) if group not in scored]

    def _module_review(self, level: str, modules: list[str]) -> list[str]:
        """
        Return the modules to review: the ones the questions came from, plus one
        module without mistakes so that new material keeps coming back.
        """
        review = list(modules)
        unseen = self._unseen_modules(level)
        if unseen:
            # All unseen modules score the same, so the pick is a random one.
            picked = self.stats.select_scored(
                [(UNSEEN_PRIORITY, group) for group in unseen], 1
            )
            review.extend(picked)
        return review

    def _module_material(self, level: str, modules: list[str]) -> list[tuple[str, list[str]]]:
        """
        Pair every module under review with the topics it covers.

        The topics are the material to work through, not a queue: nothing is
        tracked per topic, so the whole list of a module is shown every time.
        """
        by_module = self._module_topics(level)
        return [(group, by_module.get(group, [])) for group in modules]

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
        # First replay logged mistakes as real MCQ questions.  At most two per
        # module, so a single weak module cannot take over the review.
        mistake_questions = self._get_mistake_questions()
        modules = self._modules_of(mistake_questions)
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

        # Then the material of the modules those questions came from
        self._show_module_material(level, self._module_review(level, modules))

        self._show_quiz_summary(level)

    def _show_module_material(self, level: str, modules: list[str]) -> None:
        """
        Show the modules under review and the topics they cover.

        The topics are the material to work through, not a queue of items: the
        whole list of a module is shown every time, because nothing is tracked
        per topic.  The module is the unit that comes back until you log fewer
        mistakes in it.
        """
        material = self._module_material(level, modules)
        if not material:
            return

        print(f"\n📋 {len(material)} module(s) to review")
        print("Work through the topics from your book. There is no record per topic:")
        print("log the questions you get wrong with 'mistake -a', and their module")
        print("comes back first next time.\n")

        for i, (group, topics) in enumerate(material, 1):
            print(f"{'─' * 50}")
            print(f"  📖 Module {i}/{len(material)}: {group}")
            if topics:
                for topic in topics:
                    # The label repeats the module, which is the header already.
                    print(f"     • {topic_of(topic)}")
            else:
                print("     (no topics in the curriculum)")
            print(f"{'─' * 50}")

            if read_input("Press Enter for the next module ('q' quits): ").strip().upper() == "Q":
                print("👋 Quiz exited")
                return

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
        print("\nWork through each sub-question (press Enter to continue, 'q' to quit):")
        for i, q in enumerate(quiz["sub_questions"], 1):
            print(f"\n{'─' * 50}")
            print(f"  📌 Sub-question {i}/3: {q}")
            print(f"{'─' * 50}")
            print(f"  📖 Please select a question related to「{q}」from the question bank for practice.")
            if read_input("Press Enter for the next sub-question ('q' quits): ").strip().upper() == "Q":
                print("👋 Quiz exited")
                break
            print(f"  💡 Check against the standard answer; log mistakes with 'mistake -a'.")

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
        print("\n  ✅ Analysis finished.")
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
