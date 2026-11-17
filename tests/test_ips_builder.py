"""
CFA Prep CLI - Tests for the IPS builder module
Author: CodeBuddy AI Assistant
Purpose: Check the IPS template builder.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.ips_builder import IPSBuilder
from cfa_prep.utils import (
    today_iso,
)


def test_ips_builder():
    """Test the IPS builder"""
    builder = IPSBuilder()
    today = today_iso()
    # Test personal IPS generation
    path = builder.generate("personal", today)
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")
    assert "Individual Investment Policy Statement" in content
    print("  ✅ IPS builder is fine (personal)")

    # Test institutional IPS generation
    path = builder.generate("institutional", today)
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")
    assert "Institutional Investment Policy Statement" in content
    print("  ✅ IPS builder is fine (institutional)")
