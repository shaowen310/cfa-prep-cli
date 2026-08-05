# -*- coding: utf-8 -*-
"""
CFA Prep CLI - General utility functions
Author: CodeBuddy AI Assistant
Purpose: Provide project-level utility functions, including path management, file I/O, and formatted output.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any


def get_project_root() -> Path:
    """Return the project root directory (based on this file's location, two levels up: src -> root)"""
    return Path(__file__).resolve().parent.parent


def _candidate_data_root() -> Path:
    """
    Determine the data root path WITHOUT creating anything, with this priority:
      1. CFA_PREP_HOME environment variable
      2. `data_root` in <default_root>/config/settings.json
      3. ~/.cfa-prep (user home default)
    """
    env = os.environ.get("CFA_PREP_HOME")
    if env:
        return Path(env).expanduser()
    default_root = Path.home() / ".cfa-prep"
    settings = load_json(default_root / "config" / "settings.json")
    configured = settings.get("data_root")
    if configured:
        return Path(configured).expanduser()
    return default_root


def get_data_root() -> Path:
    """Return (and create) the data root directory."""
    root = _candidate_data_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_data_dir(subdir: str = "") -> Path:
    """Return the path of a specified subdirectory under the data root"""
    p = get_data_root() / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_dir() -> Path:
    """Return the config/ directory path under the data root"""
    p = get_data_root() / "config"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(filepath: Path) -> dict[str, Any]:
    """Safely load a JSON file, returning an empty dict if the file does not exist"""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(filepath: Path, data: dict[str, Any]) -> None:
    """Save data as a JSON file (UTF-8, 2-space indent)"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> dict[str, Any]:
    """Load the config/settings.json config"""
    return load_json(get_config_dir() / "settings.json")


def save_settings(settings: dict[str, Any]) -> None:
    """Save config to config/settings.json"""
    save_json(get_config_dir() / "settings.json", settings)


def today_str() -> str:
    """Return today's date string YYYYMMDD"""
    return datetime.now().strftime("%Y%m%d")


def today_iso() -> str:
    """Return today's date string YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")


def fuzzy_match(pattern: str, text: str) -> bool:
    """
    Fuzzy match: look up each character of pattern in text in order.
    Used for approximate-spelling or abbreviation searches.
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
    Search for keyword in the text and return a context snippet around it.
    window: number of characters before/after the keyword.
    """
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        # Try fuzzy match
        lines = text.split("\n")
        for line in lines:
            if fuzzy_match(keyword, line):
                return line.strip()[:window * 2]
        return "(No matching content found)"

    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def read_file_lines(filepath: Path) -> list[str]:
    """Read all lines of a file (UTF-8), returning an empty list if the file does not exist"""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return f.readlines()


def write_file_lines(filepath: Path, lines: list[str]) -> None:
    """Write a list of strings to a file (UTF-8)"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)


def read_file_text(filepath: Path) -> str:
    """Read the entire text content of a file (UTF-8)"""
    if not filepath.exists():
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file_text(filepath: Path, text: str) -> None:
    """Write text to a file (UTF-8)"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        _ = f.write(text)


def print_header(title: str) -> None:
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_section(title: str) -> None:
    """Print a formatted sub-header"""
    print(f"\n--- {title} ---")
