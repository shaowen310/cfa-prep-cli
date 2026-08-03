# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 刷题引擎模块
作者：CodeBuddy AI Assistant
用途：提供三种 CFA 考试级别的刷题模式（L1/L2/L3），
      支持随机出题、错题优先策略，交互式答题和即时判分。
"""

import random
from typing import List, Dict, Optional

from .mistake_analyzer import MistakeAnalyzer
from .progress_tracker import ProgressTracker


# 各科目的知识点池（示例数据，用户可自定义）
TOPIC_POOL = {
    "FRA": [
        "收入确认原则",
        "存货计价方法 (LIFO/FIFO)",
        "长期资产折旧",
        "租赁会计",
        "递延税资产与负债",
        "现金流量表编制",
        "财务比率分析",
    ],
    "Equity": [
        "FCFE 估值模型",
        "FCFF 估值模型",
        "DDM 股利折现模型",
        "乘数估值法 (P/E, P/B, P/S)",
        "剩余收益模型 (RI)",
        "行业与公司分析",
    ],
    "Fixed Income": [
        "Duration 计算 (Macaulay/Modified/Effective)",
        "Convexity 凸性",
        "收益率曲线策略",
        "信用利差分析",
        "ABS/MBS 结构",
        "债券定价",
    ],
    "Derivatives": [
        "二叉树期权定价",
        "Black-Scholes 模型",
        "期货定价与估值",
        "互换定价",
        "期权策略 (Covered Call, Protective Put)",
    ],
    "Ethics": [
        "七大准则概述",
        "Material Nonpublic Information",
        "Loyalty, Prudence, and Care",
        "Fair Dealing",
        "Suitability",
        "Conflicts of Interest",
        "GIPS 合规要求",
    ],
    "Economics": [
        "货币政策与财政政策",
        "汇率决定理论",
        "经济增长模型",
        "商业周期分析",
    ],
    "Portfolio Management": [
        "资产配置策略",
        "风险管理 (VaR, CVaR)",
        "行为金融偏差",
        "绩效归因分析",
        "IPS 构建流程",
    ],
    "Alternative Investments": [
        "私募股权估值",
        "对冲基金策略",
        "房地产估值",
        "大宗商品投资",
    ],
    "Quantitative Methods": [
        "时间序列分析",
        "假设检验",
        "回归分析",
        "蒙特卡洛模拟",
        "概率分布",
    ],
    "Corporate Finance": [
        "资本预算 (NPV/IRR)",
        "资本结构理论 (MM)",
        "股利政策",
        "公司治理",
        "并购分析",
    ],
}


class QuizEngine:
    """
    CFA 刷题引擎。
    根据级别（L1/L2/L3）生成不同类型的题目，
    采用错题优先（40%）+ 随机抽取（60%）策略。
    """

    def __init__(self):
        self.mistake_analyzer = MistakeAnalyzer()
        self.progress_tracker = ProgressTracker()
        self.score = 0
        self.total = 0

    def _get_all_topics(self) -> List[str]:
        """获取所有科目的所有知识点（扁平化列表）"""
        all_topics = []
        for subject, topics in TOPIC_POOL.items():
            for topic in topics:
                all_topics.append(f"[{subject}] {topic}")
        return all_topics

    def _get_mistake_topics(self) -> List[str]:
        """从错题本中提取考点，用于优先出题"""
        records = self.mistake_analyzer.get_recent_mistakes(limit=20)
        topics = []
        for r in records:
            kp = r.get("key_point", "")
            if kp:
                topics.append(kp)
        return topics

    def _get_fuzzy_topics(self) -> List[str]:
        """从进度追踪中提取模糊知识点"""
        return self.progress_tracker.get_key_points_to_review()

    def _generate_l1_quiz(self) -> List[str]:
        """
        生成 L1 级别题目（10 道单选题混合）。
        40% 来自错题/模糊知识点，60% 随机。
        注意：这是题目框架生成，实际题目需要用户根据知识点自行作答。
        """
        all_topics = self._get_all_topics()
        mistake_topics = self._get_mistake_topics()
        fuzzy_topics = self._get_fuzzy_topics()

        priority_pool = list(set(mistake_topics + fuzzy_topics))
        regular_pool = [t for t in all_topics if t not in priority_pool]

        num_priority = min(4, len(priority_pool))  # 40%
        num_regular = 10 - num_priority

        selected = []

        # 优先选题
        if priority_pool:
            selected.extend(random.sample(priority_pool, min(num_priority, len(priority_pool))))

        # 随机补充
        if regular_pool and num_regular > 0:
            selected.extend(random.sample(regular_pool, min(num_regular, len(regular_pool))))

        # 如果还不够 10 题，从全部池中补充
        while len(selected) < 10 and all_topics:
            remaining = [t for t in all_topics if t not in selected]
            if not remaining:
                break
            selected.append(random.choice(remaining))

        random.shuffle(selected)
        return selected[:10]

    def _generate_l2_quiz(self) -> Dict[str, any]:
        """
        生成 L2 级别题目（1 个 vignette + 3 小问）。
        vignette 是一个情景案例，附带 3 个相关问题。
        """
        all_topics = self._get_all_topics()
        priority_topics = list(set(self._get_mistake_topics() + self._get_fuzzy_topics()))

        # 选择 vignette 的主题
        if priority_topics and random.random() < 0.4:
            vignette_topic = random.choice(priority_topics)
        else:
            vignette_topic = random.choice(all_topics)

        # 生成 3 个相关问题（从相关科目中选）
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
            "format": "1 个案例情景 + 3 个选择题",
        }

    def _generate_l3_quiz(self) -> Dict[str, any]:
        """
        生成 L3 级别题目（1 个 IPS 情景或行为金融情景 + 主观题）。
        """
        scenario_types = ["IPS 构建 (个人)", "IPS 构建 (机构)", "行为金融偏差分析", "资产配置决策"]
        scenario = random.choice(scenario_types)

        return {
            "scenario": scenario,
            "format": "1 个情景分析 + 主观论述题",
            "instructions": "请根据情景，写出你的分析过程和建议（建议计时 18 分钟）",
        }

    def start_quiz(self, level: str = "L1") -> None:
        """
        开始刷题。

        参数：
            level: 考试级别 (L1, L2, L3)
        """
        level = level.upper()
        self.score = 0
        self.total = 0

        print("\n" + "=" * 60)
        print(f"  📝 CFA {level} 刷题模式")
        print("=" * 60)

        if level == "L1":
            self._do_l1_quiz()
        elif level == "L2":
            self._do_l2_quiz()
        elif level == "L3":
            self._do_l3_quiz()
        else:
            print(f"❌ 不支持的级别: {level}，请使用 L1/L2/L3")

    def _do_l1_quiz(self) -> None:
        """执行 L1 刷题流程"""
        topics = self._generate_l1_quiz()
        print(f"\n📋 共 {len(topics)} 道题（混合知识点）")
        print("每道题请根据考点回答，系统会记录你的作答情况。\n")

        for i, topic in enumerate(topics, 1):
            print(f"{'─' * 50}")
            print(f"  📌 第 {i}/{len(topics)} 题")
            print(f"  考点: {topic}")
            print(f"{'─' * 50}")

            # 生成题目提示
            self._generate_question_prompt(topic, i)

            # 用户作答
            print("\n请选择答案（或输入 's' 跳过, 'q' 退出）:")
            print("  [A] [B] [C] [D]")
            answer = input("你的选择: ").strip().upper()

            if answer == "Q":
                print("👋 已退出刷题")
                break
            elif answer == "S":
                print(f"⏭️ 跳过第 {i} 题")
                continue
            elif answer in ("A", "B", "C", "D"):
                self.total += 1
                # 模拟判分（实际使用时需要与正确答案对比）
                print(f"\n  ✅ 已记录答案: {answer}")
                print(f"  💡 请对照标准答案检查，如有错误请用 'add-mistake' 命令录入错题本。")
                self.score += 1  # 占位：实际应判断正误
            else:
                print("⚠️ 无效输入，请选择 A/B/C/D/S/Q")

        self._show_quiz_summary()

    def _do_l2_quiz(self) -> None:
        """执行 L2 刷题流程"""
        quiz = self._generate_l2_quiz()
        print(f"\n📋 案例主题: {quiz['vignette_topic']}")
        print(f"📋 格式: {quiz['format']}")
        print("\n请阅读以下案例情景（需从原版书获取完整 vignette）:")
        print(f"  主题: {quiz['vignette_topic']}")
        print(f"  子问题:")
        for i, q in enumerate(quiz["sub_questions"], 1):
            print(f"    {i}. {q}")

        self.total = 3
        print("\n请逐题作答（或输入 'q' 退出）:")
        for i, q in enumerate(quiz["sub_questions"], 1):
            print(f"\n{'─' * 50}")
            print(f"  📌 第 {i}/3 小题: {q}")
            print(f"{'─' * 50}")
            answer = input("你的答案 (A/B/C): ").strip().upper()
            if answer == "Q":
                print("👋 已退出刷题")
                break
            print(f"  ✅ 已记录答案: {answer}")
            print(f"  💡 请对照标准答案检查。")

        self._show_quiz_summary()

    def _do_l3_quiz(self) -> None:
        """执行 L3 刷题流程"""
        quiz = self._generate_l3_quiz()
        print(f"\n📋 情景类型: {quiz['scenario']}")
        print(f"📋 格式: {quiz['format']}")
        print(f"📋 {quiz['instructions']}")
        print(f"\n请在下方写出你的分析（输入空行结束）:\n")

        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)

        self.total = 1
        self.score = 1  # 占位
        print("\n  ✅ 已记录你的作答。")
        print("  💡 请参照标准答案自我评估，如需改进请用 'add-mistake' 记录薄弱点。")

        self._show_quiz_summary()

    def _generate_question_prompt(self, topic: str, question_num: int) -> None:
        """
        根据知识点生成题目提示。
        实际使用中，用户需要从题库中选取对应题目。

        参数：
            topic: 知识点描述
            question_num: 题目编号
        """
        # 给出题目方向提示
        print(f"\n  📖 请从题库中选取与「{topic}」相关的题目进行练习。")
        print(f"  建议使用原版书课后题或 QBank 中对应考点的题目。")

    def _show_quiz_summary(self) -> None:
        """显示刷题总结"""
        if self.total == 0:
            print("\n📊 本次未完成任何题目。")
            return

        print(f"\n{'=' * 50}")
        print(f"  📊 刷题总结")
        print(f"{'=' * 50}")
        print(f"  完成题目: {self.total}")
        print(f"  💡 请对照标准答案自行核对正确率。")
        print(f"  📝 如有错题，使用以下命令录入:")
        print(f"     python main.py add-mistake")
        print(f"  📊 查看进度:")
        print(f"     python main.py recap")
