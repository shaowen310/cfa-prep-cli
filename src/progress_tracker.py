# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 进度追踪模块
作者：CodeBuddy AI Assistant
用途：维护和更新 data/progress/progress.md 进度文件，
      追踪已掌握/仍模糊的知识点，统计错因分布，生成明日任务建议。
"""

from datetime import datetime
from typing import Dict, List

from .utils import (
    get_data_dir,
    today_iso,
    write_file_text,
    read_file_text,
)


class ProgressTracker:
    """
    进度追踪器。
    管理学习进度文件，记录已掌握和模糊的知识点，
    以及每日复习任务。
    """

    def __init__(self):
        self.progress_dir = get_data_dir("progress")
        self.progress_file = self.progress_dir / "progress.md"

    def _get_default_content(self) -> str:
        """生成默认的进度文件内容"""
        return f"""# CFA 备考进度

> 进度总览（更新于 {today_iso()}）

## 已掌握

（暂无记录）

## 仍模糊

（暂无记录）

## 错因分布

（暂无数据）

## 明日唯一任务

（暂无计划）
"""

    def load(self) -> str:
        """读取当前进度文件内容"""
        content = read_file_text(self.progress_file)
        if not content:
            content = self._get_default_content()
            write_file_text(self.progress_file, content)
        return content

    def update(
        self,
        mastered: List[str] = None,
        fuzzy: List[str] = None,
        mistake_stats: Dict[str, any] = None,
        tomorrow_task: str = "",
    ) -> None:
        """
        更新进度文件。

        参数：
            mastered: 已掌握知识点列表
            fuzzy: 仍模糊知识点列表
            mistake_stats: 错因统计（来自 MistakeAnalyzer.get_mistake_stats()）
            tomorrow_task: 明日唯一任务描述
        """
        mastered = mastered or []
        fuzzy = fuzzy or []
        mistake_stats = mistake_stats or {}

        # 格式化已掌握
        mastered_str = "\n".join(f"- {item}" for item in mastered) if mastered else "（暂无记录）"

        # 格式化仍模糊
        fuzzy_str = "\n".join(f"- {item}" for item in fuzzy) if fuzzy else "（暂无记录）"

        # 格式化错因分布
        cats = mistake_stats.get("categories", {})
        if cats:
            cat_lines = []
            for cat, pct in sorted(cats.items(), key=lambda x: x[1], reverse=True):
                cat_lines.append(f"- {cat}：{pct}%")
            cat_str = "\n".join(cat_lines)
        else:
            cat_str = "（暂无数据）"

        # 格式化明日任务
        task_str = tomorrow_task if tomorrow_task else "（暂无计划）"

        content = f"""# CFA 备考进度

> 进度总览（更新于 {today_iso()}）

## 已掌握

{mastered_str}

## 仍模糊

{fuzzy_str}

## 错因分布

{cat_str}

## 明日唯一任务

{task_str}
"""
        write_file_text(self.progress_file, content)

    def show(self) -> None:
        """在终端显示当前进度"""
        content = self.load()
        print(content)

    def interactive_update(self, mistake_stats: Dict[str, any] = None) -> None:
        """
        交互式更新进度。
        引导用户输入已掌握和模糊的知识点。
        """
        print("\n" + "=" * 50)
        print("  📊 更新学习进度")
        print("=" * 50)

        print("\n请输入已掌握的知识点（每行一个，空行结束）:")
        mastered = []
        while True:
            line = input("  > ").strip()
            if line == "":
                break
            mastered.append(line)

        print("\n请输入仍模糊的知识点（每行一个，空行结束）:")
        fuzzy = []
        while True:
            line = input("  > ").strip()
            if line == "":
                break
            fuzzy.append(line)

        tomorrow = input("\n明天的唯一任务（可选）: ").strip()

        self.update(
            mastered=mastered,
            fuzzy=fuzzy,
            mistake_stats=mistake_stats,
            tomorrow_task=tomorrow,
        )
        print(f"\n✅ 进度已更新到: {self.progress_file}")

    def get_key_points_to_review(self) -> List[str]:
        """
        从进度文件中提取需要复习的知识点。
        优先返回仍模糊的知识点。
        """
        content = self.load()
        fuzzy_points = []

        in_fuzzy = False
        for line in content.split("\n"):
            if line.startswith("## 仍模糊"):
                in_fuzzy = True
                continue
            if in_fuzzy and line.startswith("## "):
                break
            if in_fuzzy and line.strip().startswith("- "):
                point = line.strip()[2:].strip()
                if point and point != "（暂无记录）":
                    fuzzy_points.append(point)

        return fuzzy_points
