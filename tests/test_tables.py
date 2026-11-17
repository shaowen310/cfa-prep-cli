"""
CFA Prep CLI - Tests for the tables module
Author: CodeBuddy AI Assistant
Purpose: Check the parsing and the aligned rendering of the tables a question refers to.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.tables import (
    is_numeric,
    parse_table,
    render_table,
    split_row,
)


def test_split_row():
    """Test that a pasted line is split into its cells"""
    assert split_row("\tYear 1\tYear 2") == ["", "Year 1", "Year 2"]
    assert split_row("Days sales outstanding\t85\t76") == [
        "Days sales outstanding",
        "85",
        "76",
    ]
    # Two or more spaces separate the columns as well
    assert split_row("Year 1    Year 2") == ["Year 1", "Year 2"]
    # A line without a separator is a single cell
    assert split_row("Just one cell") == ["Just one cell"]
    assert split_row("   ") == []
    print("  ✅ A pasted line is split into its cells")


def test_parse_table():
    """Test that pasted lines become a table"""
    pasted = [
        "\tYear 1\tYear 2",
        "Days sales outstanding\t85\t76",
        "Days of inventory on hand\t136\t129",
        "Days payable outstanding\t29\t13",
    ]
    table = parse_table(pasted)
    assert table is not None
    # The first column holds the row labels, so its header is empty
    assert table["header"] == ["", "Year 1", "Year 2"], table
    assert len(table["rows"]) == 3, table
    assert table["rows"][0] == ["Days sales outstanding", "85", "76"], table
    assert table["rows"][2] == ["Days payable outstanding", "29", "13"], table

    # A header that is one cell short is padded at the front
    table = parse_table(["Year 1\tYear 2", "Label\t85\t76"])
    assert table is not None
    assert table["header"] == ["", "Year 1", "Year 2"], table

    # Nothing pasted is no table
    assert parse_table([]) is None
    assert parse_table(["   "]) is None
    print("  ✅ Pasted lines become a table")


def test_render_table():
    """Test that a table is rendered with aligned columns"""
    table = parse_table([
        "\tYear 1\tYear 2",
        "Days sales outstanding\t85\t76",
        "Days of inventory on hand\t136\t129",
        "Days payable outstanding\t29\t13",
    ])
    assert table is not None
    lines = render_table(table, indent="  ")
    assert len(lines) == 5, lines  # header + rule + three rows
    assert lines[0].strip().startswith("Year 1"), lines
    assert lines[2].strip().startswith("Days sales outstanding"), lines
    assert lines[2].strip().endswith("76"), lines
    # The numbers of a column end at the same place
    assert lines[3].strip().endswith("129"), lines
    assert lines[4].strip().endswith("13"), lines
    print("  ✅ A table is rendered with aligned columns")


def test_is_numeric():
    """Test that the numeric cells are recognized"""
    assert is_numeric("85")
    assert is_numeric("-1.5")
    assert is_numeric("1,200")
    assert is_numeric("12%")
    assert is_numeric("$3.50")
    assert not is_numeric("")
    assert not is_numeric("Year 1")
    print("  ✅ The numeric cells are recognized")
