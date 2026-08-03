# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 闪卡生成器模块
作者：CodeBuddy AI Assistant
用途：从知识库（data/kb/）中提取关键概念，生成 Q&A 格式闪卡，
      输出到 data/flashcards/，支持按科目分文件和导出 Anki 兼容 CSV 格式。
"""

import re
import csv
from pathlib import Path
from typing import List, Dict, Tuple

from .utils import (
    get_data_dir,
    write_file_text,
    read_file_text,
    today_str,
)
from .knowledge_base import KnowledgeBase


class FlashcardGenerator:
    """
    闪卡生成器。
    从知识库文本中自动提取关键概念，生成问答对，
    并支持导出为 Anki CSV 格式。
    """

    def __init__(self):
        self.flashcards_dir = get_data_dir("flashcards")
        self.kb = KnowledgeBase()

    def extract_concepts(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取关键概念，生成 Q&A 对。

        识别策略：
        1. 查找 "定义"、"是指"、"即"、"简称" 等模式
        2. 查找加粗/标题样式的术语
        3. 查找公式/关键数字

        参数：
            text: 知识库页面文本

        返回：
            [{"question": "...", "answer": "..."}] 列表
        """
        concepts = []

        # 模式 1: "X 是指/即 Y"
        pattern1 = re.compile(
            r"([\u4e00-\u9fff\w\s（）()（）]{2,40})[，,]?\s*(是指|即|定义为|指的是|意思是)\s*[：:]?\s*([\u4e00-\u9fff\w\s（）()（）,.，。；;！!？?]{3,200})",
        )
        for match in pattern1.finditer(text):
            term = match.group(1).strip()
            definition = match.group(3).strip()
            if len(term) >= 2 and len(definition) >= 5:
                concepts.append({
                    "question": f"什么是 {term}？",
                    "answer": definition.rstrip("。，,.") + "。",
                })

        # 模式 2: 查找英文缩写及其中文全称
        pattern2 = re.compile(
            r"([A-Z]{2,8})\s*[（(]\s*([\u4e00-\u9fff\w\s]{2,40})\s*[）)]",
        )
        for match in pattern2.finditer(text):
            abbr = match.group(1).strip()
            full = match.group(2).strip()
            if len(abbr) >= 2:
                concepts.append({
                    "question": f"{abbr} 的全称是什么？",
                    "answer": f"{abbr}：{full}。",
                })

        # 模式 3: 查找公式（包含 = 号的等式）
        pattern3 = re.compile(r"([\u4e00-\u9fff\w\s（）()（）]{2,30})\s*[:：]?\s*(.+?=.+?)(?:[，,。\n]|$)")
        for match in pattern3.finditer(text):
            name = match.group(1).strip()
            formula = match.group(2).strip()
            if len(formula) >= 5 and len(formula) <= 150:
                concepts.append({
                    "question": f"{name} 的计算公式是什么？",
                    "answer": formula.rstrip("。，,.") + "。",
                })

        # 去重（基于 question）
        seen = set()
        unique = []
        for c in concepts:
            if c["question"] not in seen:
                seen.add(c["question"])
                unique.append(c)

        return unique

    def generate_by_subject(self, subject: str = "") -> str:
        """
        按科目生成闪卡。

        参数：
            subject: 科目名称（用于筛选文件，空字符串表示全部）

        返回：
            生成的闪卡文件路径
        """
        all_data = self.kb.load_all()
        all_cards = []

        for filepath, pages in all_data.items():
            fname = Path(filepath).stem

            # 如果指定了科目，筛选文件名
            if subject and subject.lower() not in fname.lower():
                continue

            for page_num, page_text in pages.items():
                cards = self.extract_concepts(page_text)
                for card in cards:
                    card["source"] = f"{fname} (P{page_num})"
                all_cards.extend(cards)

        if not all_cards:
            return ""

        # 确定输出文件名
        if subject:
            out_name = f"{today_str()}_{subject}_flashcards.md"
        else:
            out_name = f"{today_str()}_all_flashcards.md"

        out_path = self.flashcards_dir / out_name

        # 生成 Markdown 格式闪卡
        lines = [f"# CFA 闪卡 - {subject or '全部科目'}\n", f"> 生成日期: {today_str()}\n\n"]
        for i, card in enumerate(all_cards, 1):
            lines.append(f"## 闪卡 {i}\n")
            lines.append(f"**Q**: {card['question']}\n\n")
            lines.append(f"**A**: {card['answer']}\n\n")
            lines.append(f"*来源: {card.get('source', '')}*\n\n")
            lines.append("---\n\n")

        write_file_text(out_path, "".join(lines))
        return str(out_path)

    def export_anki_csv(self, subject: str = "") -> str:
        """
        导出为 Anki 兼容的 CSV 格式。

        CSV 列：Front, Back, Tags, Source

        参数：
            subject: 科目筛选

        返回：
            生成的 CSV 文件路径
        """
        all_data = self.kb.load_all()
        all_cards = []

        for filepath, pages in all_data.items():
            fname = Path(filepath).stem
            if subject and subject.lower() not in fname.lower():
                continue

            for page_num, page_text in pages.items():
                cards = self.extract_concepts(page_text)
                for card in cards:
                    all_cards.append({
                        "Front": card["question"],
                        "Back": card["answer"],
                        "Tags": fname,
                        "Source": f"{fname} P{page_num}",
                    })

        if not all_cards:
            return ""

        out_name = f"{today_str()}_{subject or 'all'}_anki.csv"
        out_path = self.flashcards_dir / out_name

        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Front", "Back", "Tags", "Source"])
            writer.writeheader()
            writer.writerows(all_cards)

        return str(out_path)

    def interactive_generate(self) -> None:
        """交互式生成闪卡"""
        print("\n" + "=" * 50)
        print("  🃏 生成闪卡")
        print("=" * 50)

        # 显示知识库统计
        stats = self.kb.get_stats()
        print(f"\n知识库状态: {stats['total_files']} 个文件, {stats['total_pages']} 页")
        for f in stats["files"]:
            print(f"  - {f['name']} ({f['pages']} 页)")

        subject = input("\n请输入科目筛选（留空生成全部）: ").strip()

        print("\n请选择导出格式:")
        print("  [1] Markdown 格式")
        print("  [2] Anki CSV 格式")
        print("  [3] 两种都要")
        choice = input("选择 (1/2/3): ").strip()

        if choice in ("1", "3"):
            path = self.generate_by_subject(subject)
            if path:
                print(f"✅ Markdown 闪卡已生成: {path}")
            else:
                print("⚠️ 未找到匹配的知识内容")

        if choice in ("2", "3"):
            path = self.export_anki_csv(subject)
            if path:
                print(f"✅ Anki CSV 已生成: {path}")
            else:
                print("⚠️ 未找到匹配的知识内容")
