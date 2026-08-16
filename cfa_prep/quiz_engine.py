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


class MistakeQuestion(TypedDict):
    """A logged L1 MCQ mistake, replayable as a quiz question."""
    subject: str
    module: str
    key_point: str
    question: str
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
        self.score: int = 0
        self.total: int = 0
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
        options = item["options"]
        correct_text = item["correct"]
        # Shuffle so the correct answer is not always at the same position
        if self.randomize:
            random.shuffle(options)
        labels = "ABC"

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

        answer = input("\nYour answer (A/B/C): ").strip().upper()
        if answer == "Q":
            print("👋 Quiz exited")
            raise KeyboardInterrupt

        if answer in labels:
            chosen = options[labels.index(answer)]
            correct = chosen == correct_text
            self.total += 1
            if correct:
                print(f"\n  ✅ Correct! ({labels[labels.index(answer)]}. {chosen})")
                self.score += 1
            else:
                correct_label = labels[options.index(correct_text)]
                print(f"\n  ❌ Incorrect. Correct answer: {correct_label}. {correct_text}")
                # Auto-log the repeated mistake
                self._auto_log_mistake(item)
            return correct
        print("⚠️ Invalid input, please choose A/B/C")
        return False

    def _auto_log_mistake(self, item: MistakeQuestion) -> None:
        """Re-log a mistake that was answered incorrectly during review."""
        _ = self.mistake_analyzer.add_mistake(
            subject=item["subject"],
            question=item["question"],
            user_answer="",
            correct_answer=item["correct"],
            key_point=item["key_point"],
            correct_conclusion="",
            source=f"{item['subject']} > {item['module']}",
            module_name=item["module"],
            level="L1",
            options=item["options"],
        )

    def _get_fuzzy_topics(self) -> list[str]:
        """Extract fuzzy knowledge points from progress tracking"""
        return self.progress_tracker.get_key_points_to_review()

    def _generate_l1_quiz(self, level: str = "L1") -> list[str]:
        """
        Generate L1 questions (10 mixed single-choice questions).
        40% from mistakes/fuzzy knowledge points, 60% random.
        Note: This generates the question framework; actual questions are answered by the user based on the knowledge point.
        """
        all_topics = self._get_all_topics(level)
        mistake_topics = self._get_mistake_topics()
        fuzzy_topics = self._get_fuzzy_topics()

        priority_pool = list(set(mistake_topics + fuzzy_topics))
        regular_pool = [t for t in all_topics if t not in priority_pool]

        num_priority = min(4, len(priority_pool))  # 40%
        num_regular = 10 - num_priority

        selected = []

        # Priority selection
        if priority_pool:
            selected.extend(random.sample(priority_pool, min(num_priority, len(priority_pool))))

        # Random supplement
        if regular_pool and num_regular > 0:
            selected.extend(random.sample(regular_pool, min(num_regular, len(regular_pool))))

        # If still fewer than 10, supplement from the full pool
        while len(selected) < 10 and all_topics:
            remaining = [t for t in all_topics if t not in selected]
            if not remaining:
                break
            selected.append(random.choice(remaining))

        if self.randomize:
            random.shuffle(selected)
        return selected[:10]

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

        print("\n" + "=" * 60)
        print(f"  📝 CFA {level} Quiz Mode")
        print("=" * 60)

        if level == "L1":
            self._do_l1_quiz(level)
        elif level == "L2":
            self._do_l2_quiz(level)
        elif level == "L3":
            self._do_l3_quiz()
        else:
            print(f"❌ Unsupported level: {level}, please use L1/L2/L3")

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
                    self._show_quiz_summary()
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
            print("\nPlease choose an answer (or enter 's' to skip, 'q' to quit):")
            print("  [A] [B] [C] [D]")
            answer = input("Your choice: ").strip().upper()

            if answer == "Q":
                print("👋 Quiz exited")
                break
            elif answer == "S":
                print(f"⏭️ Skipped question {i}")
                continue
            elif answer in ("A", "B", "C", "D"):
                self.total += 1
                # Simulated scoring (in practice, compare with the correct answer)
                print(f"\n  ✅ Answer recorded: {answer}")
                print(f"  💡 Check against the standard answer; if wrong, use the 'mistake -a' command to log it.")
                self.score += 1  # Placeholder: should judge correctness in practice
            else:
                print("⚠️ Invalid input, please choose A/B/C/D/S/Q")

        self._show_quiz_summary()

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

        self.total = 3
        print("\nPlease answer each question (or enter 'q' to quit):")
        for i, q in enumerate(quiz["sub_questions"], 1):
            print(f"\n{'─' * 50}")
            print(f"  📌 Sub-question {i}/3: {q}")
            print(f"{'─' * 50}")
            answer = input("Your answer (A/B/C): ").strip().upper()
            if answer == "Q":
                print("👋 Quiz exited")
                break
            print(f"  ✅ Answer recorded: {answer}")
            print(f"  💡 Check against the standard answer.")

        self._show_quiz_summary()

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

        self._show_quiz_summary()

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

    def _show_quiz_summary(self) -> None:
        """Show the quiz summary"""
        if self.total == 0:
            print("\n📊 No questions completed this time.")
            return

        print(f"\n{'=' * 50}")
        print(f"  📊 Quiz Summary")
        print(f"{'=' * 50}")
        print(f"  Questions completed: {self.total}")
        print(f"  💡 Check your accuracy rate against the standard answers.")
        print(f"  📝 For any mistakes, log them with the following command:")
        print(f"     cfa-prep mistake -a")
        print(f"  📊 View progress:")
        print(f"     cfa-prep recap")
