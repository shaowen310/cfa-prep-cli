"""
CFA Prep CLI - Tests for the utils module
Author: CodeBuddy AI Assistant
Purpose: Check the helpers of the utils module: the data root, the search helpers and the keyword handling.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.utils import (
    clean_keyword,
    extract_context,
    fuzzy_match,
    get_data_dir,
    get_project_root,
)


def test_project_root():
    """Test whether the project root directory is correct"""
    root = get_project_root()
    assert root.exists(), "Project root directory does not exist"
    assert (root / "cfa_prep").exists(), "cfa_prep directory does not exist"
    print(f"  ✅ Project root: {root}")


def test_data_dirs():
    """Test data directory creation"""
    dirs = ["mistakes", "progress", "flashcards", "curriculum", "templates"]
    for d in dirs:
        p = get_data_dir(d)
        assert p.exists(), f"{d} directory creation failed"
    print("  ✅ All data directories are fine")


def test_fuzzy_match():
    """Test fuzzy matching"""
    assert fuzzy_match("FCFE", "Free Cash Flow to Equity") == True
    assert fuzzy_match("xyz", "Free Cash Flow to Equity") == False
    assert fuzzy_match("fcfe", "FCFE") == True
    print("  ✅ Fuzzy matching is fine")


def test_extract_context():
    """Test context extraction"""
    text = "The Free Cash Flow to Equity (FCFE) model values a company based on cash available to shareholders."
    snippet = extract_context(text, "FCFE")
    assert "FCFE" in snippet
    print("  ✅ Context extraction is fine")


def test_clean_keyword():
    """Test that the typed words become one keyword, with or without quotes"""
    assert clean_keyword(["FCFE"]) == "FCFE"
    assert clean_keyword(["free", "cash", "flow"]) == "free cash flow"
    assert clean_keyword(['"free cash flow"']) == "free cash flow"
    assert clean_keyword(["'free cash flow'"]) == "free cash flow"
    assert clean_keyword([]) == ""
    print("  ✅ The keyword is built from the typed words")
