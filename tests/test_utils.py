"""
CFA Prep CLI - Tests for the utils module
Author: CodeBuddy AI Assistant
Purpose: Check the helpers of the utils module: the data root, the search helpers and the keyword handling.
"""

import sys
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.utils import (
    clean_keyword,
    extract_context,
    fuzzy_match,
    get_data_dir,
    get_project_root,
    load_json,
    save_json,
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


def test_save_json_is_atomic():
    """Test that a JSON file is written safely and never half-written"""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "data.json"

        # The file is written and read back
        save_json(target, {"records": [{"question": "A question"}]})
        assert target.is_file()
        assert load_json(target).get("records") == [{"question": "A question"}]
        # No half-written file is left behind
        assert not target.with_name(target.name + ".tmp").exists()

        # A write that fails leaves the old file alone
        try:
            save_json(target, {"records": {1, 2}})  # a set cannot be written
        except TypeError:
            pass
        else:
            raise AssertionError("a value that cannot be written must raise")
        assert load_json(target).get("records") == [{"question": "A question"}]
        assert not target.with_name(target.name + ".tmp").exists()
    print("  ✅ A JSON file is written safely and never half-written")
