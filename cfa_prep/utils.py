"""
CFA Prep CLI - General utility functions
Author: CodeBuddy AI Assistant
Purpose: Provide project-level utility functions, including path management, file I/O, and formatted output.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import cast

HASH_LENGTH = 16  # number of hex characters kept from a hash

# The punctuation that only closes a question and carries no meaning of its own
CLOSING_PUNCTUATION = ".:;!?。！？"


def normalize_text(text: str) -> str:
    """Collapse whitespace and case so cosmetic edits keep the same identity."""
    return " ".join(text.split()).casefold()


def stem_key(text: str) -> str:
    """
    Return the text that recognises a question that is already logged.

    The key ignores what is only cosmetic: the case, the spacing and the
    punctuation that closes the sentence.  "What is X?" and "what is x" are the
    same question, so they have to be recognised as one — otherwise the
    duplicate is never noticed and the question is logged a second time.
    """
    return normalize_text(text).rstrip(CLOSING_PUNCTUATION).strip()


def ends_with_punctuation(text: str) -> bool:
    """Tell whether the text ends with the punctuation that closes a sentence."""
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in CLOSING_PUNCTUATION


def capitalize_first(text: str) -> str:
    """Write the first letter of a sentence in upper case."""
    if not text or not text[0].islower():
        return text
    return text[0].upper() + text[1:]


def prefer_text(old: str, new: str) -> str:
    """
    Return the variant of a text that is written the most carefully.

    The variant that ends with punctuation wins over the one that does not:
    "general partnerships." is the whole text, "general partnerships" is the
    same text with the point left out.  When both are written the same way,
    the newer one wins.
    """
    if not old:
        return new
    if not new:
        return old
    if ends_with_punctuation(new) != ends_with_punctuation(old):
        return new if ends_with_punctuation(new) else old
    return new


def hash_text(*parts: str) -> str:
    """Return a short, stable hash for the given text parts."""
    digest = hashlib.sha1()
    for part in parts:
        digest.update(normalize_text(part).encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()[:HASH_LENGTH]


def get_project_root() -> Path:
    """Return the project root directory (based on this file's location, two levels up: src -> root)"""
    return Path(__file__).resolve().parent.parent


def _default_config_dir() -> Path:
    """Stable anchor config dir under the default ~/.cfa-prep, independent of the
    currently-resolved data root. home.env lives here so it can redirect resolution."""
    return Path.home() / ".cfa-prep" / "config"


def get_home_env_file() -> Path:
    """Path of the file that persists the data root override (home.env)."""
    return _default_config_dir() / "home.env"


def _candidate_data_root() -> Path:
    """
    Determine the data root path WITHOUT creating anything, with this priority:
      1. CFA_PREP_HOME environment variable
      2. ~/.cfa-prep/config/home.env (written by `cfa-prep config home <path>`)
      3. ~/.cfa-prep (user home default)
    """
    env = os.environ.get("CFA_PREP_HOME")
    if env:
        return Path(env).expanduser()
    home_env_file = _default_config_dir() / "home.env"
    if home_env_file.exists():
        for line in home_env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "CFA_PREP_HOME":
                    return Path(v.strip()).expanduser()
    return Path.home() / ".cfa-prep"


def load_home_env() -> None:
    """
    Source config/home.env to set CFA_PREP_HOME if it is not already set in the
    process environment. This lets `cfa-prep config home <path>` persist the data
    root without storing it inside settings.json.
    """
    if os.environ.get("CFA_PREP_HOME"):
        return
    home_env_file = _default_config_dir() / "home.env"
    if not home_env_file.exists():
        return
    for line in home_env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            _ = os.environ.setdefault(k.strip(), v.strip())


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


def set_home_env(new_root: str | Path) -> Path:
    """
    Persist the data root to config/home.env so future runs resolve the same folder.
    Returns the resolved path. This is honored by load_home_env() at startup and never
    stored inside settings.json (the data root is controlled via the CFA_PREP_HOME env var).
    """
    resolved = Path(new_root).expanduser().resolve()
    home_env_file = get_home_env_file()
    home_env_file.parent.mkdir(parents=True, exist_ok=True)
    write_file_text(home_env_file, f"CFA_PREP_HOME={resolved}\n")
    return resolved


def set_setting(key: str, value: object) -> None:
    """Merge a single key/value into config/settings.json."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def load_json(filepath: Path) -> dict[str, object]:
    """Safely load a JSON file, returning an empty dict if the file does not exist"""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return cast(dict[str, object], json.load(f))
    return {}


def save_json(filepath: Path, data: dict[str, object]) -> None:
    """
    Save data as a JSON file (UTF-8, 2-space indent).

    The file is written next to the target and then moved over it, so an
    interrupted write never destroys the file that was there before.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp = filepath.with_name(filepath.name + ".tmp")
    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(temp, filepath)
    except BaseException:
        # The old file is still there, so only the half-written one is removed
        temp.unlink(missing_ok=True)
        raise


def _replace_with_retry(temp: Path, target: Path, attempts: int = 5) -> None:
    """
    Move the temporary file over the target, retrying a little.

    Windows refuses the move when another program holds the target open for a
    moment — a cloud sync client or the virus scanner does that on its own.
    The target is only ever replaced by a complete file, so waiting a little
    is enough to get the write through.
    """
    for attempt in range(attempts):
        try:
            os.replace(temp, target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def load_settings() -> dict[str, object]:
    """Load the config/settings.json config"""
    return load_json(get_config_dir() / "settings.json")


def save_settings(settings: dict[str, object]) -> None:
    """Save config to config/settings.json"""
    save_json(get_config_dir() / "settings.json", settings)


def today_str() -> str:
    """Return today's date string YYYYMMDD"""
    return datetime.now().astimezone().strftime("%Y%m%d")


def today_iso() -> str:
    """Return today's date string YYYY-MM-DD"""
    return datetime.now().astimezone().strftime("%Y-%m-%d")


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


def word_pattern(keyword: str) -> re.Pattern[str]:
    """Build a case-insensitive regex that matches the keyword as a whole word."""
    return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)


def contains_word(text: str, keyword: str) -> bool:
    """
    Return True when the keyword appears in the text as a whole word.

    "tariff" matches "a tariff" and "(tariffs are ...)" is not a match for
    "tariff" — the keyword has to be a word of its own.
    """
    if not keyword.strip():
        return False
    return bool(word_pattern(keyword.strip()).search(text))


def fuzzy_word_match(text: str, keyword: str) -> bool:
    """
    Return True when a whole word of the text fuzzy-matches the keyword.

    The fuzzy match is applied per word, so an abbreviation still finds its
    word ("FCFE" -> "Free Cash Flow to Equity") without matching every text
    that happens to contain the letters in order.
    """
    keyword = keyword.strip()
    if not keyword:
        return False
    for word in re.findall(r"\w+", text):
        if fuzzy_match(keyword, word):
            return True
    return False


def clean_keyword(words: list[str]) -> str:
    """
    Turn the words typed on the command line into one search keyword.

    The words are joined with a space, so a phrase can be typed without quotes,
    and the quotes are stripped when the shell kept them.
    """
    text = " ".join(word for word in words if word).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


def find_keyword(text: str, keyword: str) -> int:
    """
    Return the index of the keyword in the text, or -1.

    A whole-word hit is preferred, so the snippet shows the word that matched
    and not an occurrence inside another word.
    """
    keyword = keyword.strip()
    if keyword:
        match = word_pattern(keyword).search(text)
        if match:
            return match.start()
    return text.lower().find(keyword.lower())


def extract_context(text: str, keyword: str, window: int = 80) -> str:
    """
    Search for keyword in the text and return a context snippet around it.
    window: number of characters before/after the keyword.
    """
    idx = find_keyword(text, keyword)
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


def write_file_text(filepath: Path, text: str) -> None:
    """Write text to a file (UTF-8)"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        _ = f.write(text)


def print_header(title: str) -> None:
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_section(title: str) -> None:
    """Print a formatted sub-header"""
    print(f"\n--- {title} ---")
