# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 知识库管理模块
作者：CodeBuddy AI Assistant
用途：读取 data/kb/ 下的 TXT 知识文件，按页码分块，支持关键词搜索（正则 + 模糊匹配）。
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .utils import (
    get_data_dir,
    fuzzy_match,
    extract_context,
    read_file_text,
)


class KnowledgeBase:
    """
    CFA 知识库管理器。
    负责扫描 data/kb/ 目录下的 .txt 文件，
    按 "===== PAGE N =====" 标记分页，
    提供关键词搜索功能。
    """

    def __init__(self):
        self.kb_dir = get_data_dir("kb")
        # 缓存：{文件路径: {页码: 页面文本}}
        self._cache: Dict[str, Dict[int, str]] = {}

    def scan_files(self) -> List[Path]:
        """扫描 data/kb/ 下的所有 .txt 文件"""
        return sorted(self.kb_dir.glob("*.txt"))

    def load_file(self, filepath: Path) -> Dict[int, str]:
        """
        加载单个知识文件，按页码分块。
        返回 {页码: 页面文本} 字典。
        页码标记格式：===== PAGE N =====
        """
        if str(filepath) in self._cache:
            return self._cache[str(filepath)]

        text = read_file_text(filepath)
        pages: Dict[int, str] = {}

        # 按 ===== PAGE N ===== 分割
        # 使用正则匹配页码标记
        pattern = r"^=====\s*PAGE\s+(\d+)\s*=====\s*$"
        parts = re.split(pattern, text, flags=re.MULTILINE)

        # parts[0] 是第一页标记之前的内容（如果有的话）
        # 然后是 (页码1, 内容1, 页码2, 内容2, ...)
        if len(parts) > 1:
            # 跳过 parts[0]（第一个标记之前的内容，如果有的话）
            start = 0
            if not re.match(pattern, parts[0].strip(), re.MULTILINE):
                # parts[0] 是标记前内容，当作第 0 页
                if parts[0].strip():
                    pages[0] = parts[0].strip()
                start = 1

            for i in range(start, len(parts) - 1, 2):
                try:
                    page_num = int(parts[i])
                    page_text = parts[i + 1].strip()
                    if page_text:
                        pages[page_num] = page_text
                except (ValueError, IndexError):
                    continue
        else:
            # 没有页码标记，整个文件作为一页
            pages[1] = text.strip()

        self._cache[str(filepath)] = pages
        return pages

    def load_all(self) -> Dict[str, Dict[int, str]]:
        """加载所有知识文件"""
        result = {}
        for fp in self.scan_files():
            result[str(fp)] = self.load_file(fp)
        return result

    def search(
        self,
        keyword: str,
        use_regex: bool = False,
        use_fuzzy: bool = True,
        max_results: int = 10,
    ) -> List[Dict[str, any]]:
        """
        在所有知识文件中搜索关键词。

        参数：
            keyword: 搜索关键词
            use_regex: 是否使用正则表达式搜索
            use_fuzzy: 是否启用模糊匹配（拼写近似）
            max_results: 最多返回结果数

        返回：
            [{file, page, snippet}] 列表
        """
        results = []
        all_data = self.load_all()

        for filepath, pages in all_data.items():
            fname = os.path.basename(filepath)
            for page_num, page_text in pages.items():
                matched = False
                snippet = ""

                if use_regex:
                    try:
                        if re.search(keyword, page_text, re.IGNORECASE):
                            matched = True
                            snippet = extract_context(page_text, keyword)
                    except re.error:
                        # 正则表达式有误，回退到普通搜索
                        pass

                if not matched and use_fuzzy:
                    # 先尝试精确包含匹配
                    if keyword.lower() in page_text.lower():
                        matched = True
                        snippet = extract_context(page_text, keyword)
                    # 再尝试模糊匹配
                    elif fuzzy_match(keyword, page_text):
                        matched = True
                        snippet = extract_context(page_text, keyword)

                if not matched:
                    # 普通包含匹配
                    if keyword.lower() in page_text.lower():
                        matched = True
                        snippet = extract_context(page_text, keyword)

                if matched:
                    results.append({
                        "file": fname,
                        "filepath": filepath,
                        "page": page_num,
                        "snippet": snippet,
                    })

                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        return results[:max_results]

    def get_stats(self) -> Dict[str, any]:
        """获取知识库统计信息"""
        files = self.scan_files()
        total_pages = 0
        file_stats = []

        for fp in files:
            pages = self.load_file(fp)
            total_pages += len(pages)
            file_stats.append({
                "name": fp.name,
                "pages": len(pages),
            })

        return {
            "total_files": len(files),
            "total_pages": total_pages,
            "files": file_stats,
        }

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
