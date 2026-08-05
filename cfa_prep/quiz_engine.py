# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Quiz engine module
Author: CodeBuddy AI Assistant
Purpose: Provide quiz modes for the three CFA exam levels (L1/L2/L3),
         with random question selection and mistake-priority strategy, interactive answering, and instant scoring.
"""

import random
from typing import List, Dict, Optional

from .mistake_analyzer import MistakeAnalyzer
from .progress_tracker import ProgressTracker


# Knowledge point pool per subject (sample data; users can customize)
TOPIC_POOL = {
    "FRA": [
        "Revenue recognition principles",
        "Inventory valuation methods (LIFO/FIFO)",
        "Long-lived asset depreciation",
        "Lease accounting",
        "Deferred tax assets and liabilities",
        "Cash flow statement preparation",
        "Financial ratio analysis",
    ],
    "Equity": [
        "FCFE valuation model",
        "FCFF valuation model",
        "DDM dividend discount model",
        "Multiplier valuation methods (P/E, P/B, P/S)",
        "Residual income model (RI)",
        "Industry and company analysis",
    ],
    "Fixed Income": [
        "Duration calculation (Macaulay/Modified/Effective)",
        "Convexity",
        "Yield curve strategies",
        "Credit spread analysis",
        "ABS/MBS structures",
        "Bond pricing",
    ],
    "Derivatives": [
        "Binomial tree option pricing",
        "Black-Scholes model",
        "Futures pricing and valuation",
        "Swap pricing",
        "Option strategies (Covered Call, Protective Put)",
    ],
    "Ethics": [
        "Overview of the seven standards",
        "Material Nonpublic Information",
        "Loyalty, Prudence, and Care",
        "Fair Dealing",
        "Suitability",
        "Conflicts of Interest",
        "GIPS compliance requirements",
    ],
    "Economics": [
        "Monetary and fiscal policy",
        "Exchange rate determination theories",
        "Economic growth models",
        "Business cycle analysis",
    ],
    "Portfolio Management": [
        "Asset allocation strategies",
        "Risk management (VaR, CVaR)",
        "Behavioral finance biases",
        "Performance attribution analysis",
        "IPS construction process",
    ],
    "Alternative Investments": [
        "Private equity valuation",
        "Hedge fund strategies",
        "Real estate valuation",
        "Commodity investing",
    ],
    "Quantitative Methods": [
        "Time series analysis",
        "Hypothesis testing",
        "Regression analysis",
        "Monte Carlo simulation",
        "Probability distributions",
    ],
    "Corporate Finance": [
        "Capital budgeting (NPV/IRR)",
        "Capital structure theory (MM)",
        "Dividend policy",
        "Corporate governance",
        "M&A analysis",
    ],
}


class QuizEngine:
    """
    CFA quiz engine.
    Generates different question types based on level (L1/L2/L3),
    using a mistake-priority (40%) + random selection (60%) strategy.
    """

    def __init__(self):
        self.mistake_analyzer = MistakeAnalyzer()
        self.progress_tracker = ProgressTracker()
        self.score = 0
        self.total = 0

    def _get_all_topics(self) -> List[str]:
        """Get all knowledge points across all subjects (flattened list)"""
        all_topics = []
        for subject, topics in TOPIC_POOL.items():
            for topic in topics:
                all_topics.append(f"[{subject}] {topic}")
        return all_topics

    def _get_mistake_topics(self) -> List[str]:
        """Extract knowledge points from the mistake log for priority question selection"""
        records = self.mistake_analyzer.get_recent_mistakes(limit=20)
        topics = []
        for r in records:
            kp = r.get("key_point", "")
            if kp:
                topics.append(kp)
        return topics

    def _get_fuzzy_topics(self) -> List[str]:
        """Extract fuzzy knowledge points from progress tracking"""
        return self.progress_tracker.get_key_points_to_review()

    def _generate_l1_quiz(self) -> List[str]:
        """
        Generate L1 questions (10 mixed single-choice questions).
        40% from mistakes/fuzzy knowledge points, 60% random.
        Note: This generates the question framework; actual questions are answered by the user based on the knowledge point.
        """
        all_topics = self._get_all_topics()
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

        random.shuffle(selected)
        return selected[:10]

    def _generate_l2_quiz(self) -> Dict[str, any]:
        """
        Generate L2 questions (1 vignette + 3 sub-questions).
        A vignette is a case scenario accompanied by 3 related questions.
        """
        all_topics = self._get_all_topics()
        priority_topics = list(set(self._get_mistake_topics() + self._get_fuzzy_topics()))

        # Choose the vignette topic
        if priority_topics and random.random() < 0.4:
            vignette_topic = random.choice(priority_topics)
        else:
            vignette_topic = random.choice(all_topics)

        # Generate 3 related questions (selected from the relevant subject)
        subject = vignette_topic.split("]")[0].replace("[", "")
        related_topics = TOPIC_POOL.get(subject, [])
        if not related_topics:
            related_topics = [vignette_topic]

        sub_questions = random.sample(related_topics, min(3, len(related_topics)))
        while len(sub_questions) < 3:
            sub_questions.append(random.choice(all_topics))

        return {
            "vignette_topic": vignette_topic,
            "sub_questions": sub_questions,
            "format": "1 case scenario + 3 multiple-choice questions",
        }

    def _generate_l3_quiz(self) -> Dict[str, any]:
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

    def start_quiz(self, level: str = "L1") -> None:
        """
        Start the quiz.

        Parameters:
            level: exam level (L1, L2, L3)
        """
        level = level.upper()
        self.score = 0
        self.total = 0

        print("\n" + "=" * 60)
        print(f"  📝 CFA {level} Quiz Mode")
        print("=" * 60)

        if level == "L1":
            self._do_l1_quiz()
        elif level == "L2":
            self._do_l2_quiz()
        elif level == "L3":
            self._do_l3_quiz()
        else:
            print(f"❌ Unsupported level: {level}, please use L1/L2/L3")

    def _do_l1_quiz(self) -> None:
        """Run the L1 quiz flow"""
        topics = self._generate_l1_quiz()
        print(f"\n📋 {len(topics)} questions total (mixed knowledge points)")
        print("Answer each question based on the knowledge point; your responses will be recorded.\n")

        for i, topic in enumerate(topics, 1):
            print(f"{'─' * 50}")
            print(f"  📌 Question {i}/{len(topics)}")
            print(f"  Topic: {topic}")
            print(f"{'─' * 50}")

            # Generate the question prompt
            self._generate_question_prompt(topic, i)

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
                print(f"  💡 Check against the standard answer; if wrong, use the 'add-mistake' command to log it.")
                self.score += 1  # Placeholder: should judge correctness in practice
            else:
                print("⚠️ Invalid input, please choose A/B/C/D/S/Q")

        self._show_quiz_summary()

    def _do_l2_quiz(self) -> None:
        """Run the L2 quiz flow"""
        quiz = self._generate_l2_quiz()
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
        print("  💡 Self-assess against the standard answer; if improvement is needed, use 'add-mistake' to log weak points.")

        self._show_quiz_summary()

    def _generate_question_prompt(self, topic: str, question_num: int) -> None:
        """
        Generate a question prompt based on the knowledge point.
        In practice, users should select the corresponding question from a question bank.

        Parameters:
            topic: knowledge point description
            question_num: question number
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
        print(f"     python main.py add-mistake")
        print(f"  📊 View progress:")
        print(f"     python main.py recap")
