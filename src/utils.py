# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 通用工具函数
作者：CodeBuddy AI Assistant
用途：提供项目级的通用工具函数，包括路径管理、文件读写、格式化输出等。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any


def get_project_root() -> Path:
    """获取项目根目录（基于本文件位置向上两级：src -> 根目录）"""
    return Path(__file__).resolve().parent.parent


def get_data_dir(subdir: str = "") -> Path:
    """获取 data/ 下指定子目录的路径"""
    p = get_project_root() / "data" / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_dir() -> Path:
    """获取 config/ 目录路径"""
    p = get_project_root() / "config"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(filepath: Path) -> dict[str, Any]:
    """安全加载 JSON 文件，文件不存在时返回空字典"""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(filepath: Path, data: dict[str, Any]) -> None:
    """保存数据为 JSON 文件（UTF-8，缩进 2 空格）"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> dict[str, Any]:
    """加载 config/settings.json 配置"""
    return load_json(get_config_dir() / "settings.json")


def save_settings(settings: dict[str, Any]) -> None:
    """保存配置到 config/settings.json"""
    save_json(get_config_dir() / "settings.json", settings)


def today_str() -> str:
    """返回当天日期字符串 YYYYMMDD"""
    return datetime.now().strftime("%Y%m%d")


def today_iso() -> str:
    """返回当天日期字符串 YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")


def fuzzy_match(pattern: str, text: str) -> bool:
    """
    模糊匹配：将 pattern 中的每个字符按顺序在 text 中查找。
    用于拼写近似或缩写搜索。
    """
    pattern = pattern.lower()
    text = text.lower()
    idx = 0
    for ch in pattern:
        idx = text.find(ch, idx)
        if idx == -1:
            return False
        idx += 1
    return True


def extract_context(text: str, keyword: str, window: int = 80) -> str:
    """
    在文本中搜索关键词，返回关键词周围的上下文片段。
    window: 关键词前后的字符数。
    """
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        # 尝试模糊匹配
        lines = text.split("\n")
        for line in lines:
            if fuzzy_match(keyword, line):
                return line.strip()[:window * 2]
        return "（未找到匹配内容）"

    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def read_file_lines(filepath: Path) -> list[str]:
    """读取文件所有行（UTF-8），文件不存在返回空列表"""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return f.readlines()


def write_file_lines(filepath: Path, lines: list[str]) -> None:
    """将字符串列表写入文件（UTF-8）"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)


def read_file_text(filepath: Path) -> str:
    """读取文件全部文本内容（UTF-8）"""
    if not filepath.exists():
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file_text(filepath: Path, text: str) -> None:
    """将文本写入文件（UTF-8）"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        _ = f.write(text)


def print_header(title: str) -> None:
    """打印格式化的标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_section(title: str) -> None:
    """打印格式化的子标题"""
    print(f"\n--- {title} ---")
