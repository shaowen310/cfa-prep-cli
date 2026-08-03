# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 错题分析器模块
作者：CodeBuddy AI Assistant
用途：录入和分析错题，按三类归类（概念不清/计算错误/审题失误），
      自动写入 data/mistakes/ 目录，并生成复习建议。
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from .utils import (
    get_data_dir,
    today_str,
    write_file_text,
    read_file_text,
    load_json,
    save_json,
)


# 错因分类
MISTAKE_CATEGORIES = {
    "1": "概念不清",
    "2": "计算错误",
    "3": "审题失误",
}


class MistakeAnalyzer:
    """
    错题分析器。
    管理错题的录入、分类、存储和检索。
    """

    def __init__(self):
        self.mistakes_dir = get_data_dir("mistakes")
        self.index_file = self.mistakes_dir / "mistakes_index.json"
        self.index = load_json(self.index_file)

    def _save_index(self) -> None:
        """保存错题索引"""
        save_json(self.index_file, self.index)

    def add_mistake(
        self,
        subject: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        category: str,
        key_point: str,
        correct_conclusion: str,
        source: str = "",
    ) -> str:
        """
        添加一条错题记录。

        参数：
            subject: 科目名称（如 FRA, Equity, Ethics）
            question: 题目描述
            user_answer: 用户的错误答案
            correct_answer: 正确答案
            category: 错因分类（概念不清/计算错误/审题失误）
            key_point: 考点（一句话）
            correct_conclusion: 正确结论（一句话）
            source: 出处（如 @data/kb/l2_vol3_p120-180.txt (P145)）

        返回：
            生成的错题文件路径
        """
        date_str = today_str()
        category_short = category.replace(" ", "_")
        filename = f"{date_str}_{subject}_{category_short}.md"
        filepath = self.mistakes_dir / filename

        # 检查是否已有同一天的错题文件，有则追加
        existing = read_file_text(filepath)

        entry = f"""
### 错题记录

**日期**: {date_str}
**科目**: {subject}
**错因**: {category}
**考点**: {key_point}
**正确结论**: {correct_conclusion}
**出处**: {source if source else "（未指定）"}

---

**题目**:
{question}

**我的答案**: {user_answer}

**正确答案**: {correct_answer}

---

"""
        if existing:
            write_file_text(filepath, existing + "\n" + entry)
        else:
            write_file_text(filepath, entry)

        # 更新索引
        if "records" not in self.index:
            self.index["records"] = []

        self.index["records"].append({
            "date": date_str,
            "subject": subject,
            "category": category,
            "key_point": key_point,
            "file": filename,
        })
        self._save_index()

        return str(filepath)

    def add_mistake_interactive(self) -> None:
        """
        交互式录入错题。
        引导用户逐步输入错题信息。
        """
        print("\n" + "=" * 50)
        print("  📝 录入错题")
        print("=" * 50)

        subject = input("科目（如 FRA, Equity, Ethics）: ").strip()
        if not subject:
            print("❌ 科目不能为空")
            return

        print("\n请输入题目描述（输入空行结束）:")
        question_lines = []
        while True:
            line = input()
            if line == "":
                break
            question_lines.append(line)
        question = "\n".join(question_lines)
        if not question.strip():
            print("❌ 题目不能为空")
            return

        user_answer = input("\n你的答案: ").strip()
        correct_answer = input("正确答案: ").strip()

        print("\n错因分类:")
        for key, value in MISTAKE_CATEGORIES.items():
            print(f"  [{key}] {value}")
        cat_choice = input("选择错因分类 (1/2/3): ").strip()
        category = MISTAKE_CATEGORIES.get(cat_choice, "概念不清")

        key_point = input("\n考点（一句话总结）: ").strip()
        correct_conclusion = input("正确结论（一句话总结）: ").strip()
        source = input("出处（如 @data/kb/l2_vol3_p120-180.txt (P145)）: ").strip()

        filepath = self.add_mistake(
            subject=subject,
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer,
            category=category,
            key_point=key_point,
            correct_conclusion=correct_conclusion,
            source=source,
        )
        print(f"\n✅ 错题已保存到: {filepath}")

    def get_recent_mistakes(self, limit: int = 10) -> List[Dict]:
        """
        获取最近 N 条错题记录。
        按日期降序排列。
        """
        records = self.index.get("records", [])
        records.sort(key=lambda r: r.get("date", ""), reverse=True)
        return records[:limit]

    def get_mistake_stats(self) -> Dict[str, any]:
        """
        获取错题统计数据。
        返回各类错因的数量和百分比。
        """
        records = self.index.get("records", [])
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "categories": {},
                "subjects": {},
                "key_points": [],
            }

        # 统计错因分布
        cat_count: Dict[str, int] = {}
        for r in records:
            cat = r.get("category", "未分类")
            cat_count[cat] = cat_count.get(cat, 0) + 1

        cat_pct = {k: round(v / total * 100, 1) for k, v in cat_count.items()}

        # 统计科目分布
        subj_count: Dict[str, int] = {}
        for r in records:
            subj = r.get("subject", "未知")
            subj_count[subj] = subj_count.get(subj, 0) + 1

        # 提取所有考点
        key_points = [r.get("key_point", "") for r in records if r.get("key_point")]

        return {
            "total": total,
            "categories": cat_pct,
            "subjects": subj_count,
            "key_points": key_points,
        }

    def list_mistake_files(self) -> List[Path]:
        """列出所有错题文件"""
        return sorted(
            [f for f in self.mistakes_dir.glob("*.md") if f.name != "mistakes_index.json"],
            reverse=True,
        )
