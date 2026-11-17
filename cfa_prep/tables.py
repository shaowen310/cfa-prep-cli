"""
CFA Prep CLI - Table module
Author: CodeBuddy AI Assistant
Purpose: Store and display the small data tables a question may refer to
         ("Based on the table below, ...").  A table is typed once, pasted as
         text, and shown aligned again every time the question comes back.
"""

import re
from typing import TypedDict


class Table(TypedDict):
    """A table of a question: a header row and the data rows below it."""
    header: list[str]
    rows: list[list[str]]


def split_row(line: str) -> list[str]:
    """
    Split one pasted line into its cells.

    The columns are separated by tabs, or by two or more spaces.  A line with
    neither is a single cell.  A leading tab is kept: it is the empty header
    of the column that holds the row labels.
    """
    line = line.rstrip()
    if not line.strip():
        return []
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t")]
    stripped = line.strip()
    if "  " in stripped:
        return [cell.strip() for cell in re.split(r"\s{2,}", stripped)]
    return [stripped]


def parse_table(lines: list[str]) -> Table | None:
    """
    Parse pasted lines into a table.

    The first line is the header, the lines below it are the data rows.  A table
    without any content returns None.
    """
    rows = [split_row(line) for line in lines]
    rows = [row for row in rows if row]
    if not rows:
        return None
    header = rows[0]
    data = rows[1:]
    columns = max([len(header)] + [len(row) for row in data])
    if len(header) == columns - 1:
        # The first column holds the row labels, so its header is empty
        header = [""] + header
    return {"header": header, "rows": data}


def is_numeric(text: str) -> bool:
    """Return True when the cell is a number, so the column can be right-aligned."""
    stripped = text.strip().replace(",", "").replace("%", "").replace("$", "")
    if not stripped:
        return False
    try:
        _ = float(stripped)
    except ValueError:
        return False
    return True


def render_table(table: Table, indent: str = "  ", rule: str = "─") -> list[str]:
    """
    Return the lines of the table with the columns aligned.

    A column of numbers is right-aligned, a column of words is left-aligned.
    """
    header = [cell.strip() for cell in table.get("header", [])]
    rows = [[cell.strip() for cell in row] for row in table.get("rows", [])]
    if not header and not rows:
        return []

    # Every row has the same number of cells
    columns = max([len(header)] + [len(row) for row in rows])
    header = header + [""] * (columns - len(header))
    rows = [row + [""] * (columns - len(row)) for row in rows]

    # The width of a column is the widest cell in it
    widths = []
    for index in range(columns):
        cells = [header[index]] + [row[index] for row in rows]
        widths.append(max(len(cell) for cell in cells))

    def format_row(cells: list[str]) -> str:
        parts = []
        for index, cell in enumerate(cells):
            if is_numeric(cell):
                parts.append(cell.rjust(widths[index]))
            else:
                parts.append(cell.ljust(widths[index]))
        return (indent + "  ".join(parts)).rstrip()

    lines = []
    if any(header):
        lines.append(format_row(header))
        lines.append(indent + "  ".join(rule * width for width in widths))
    lines.extend(format_row(row) for row in rows)
    return lines