"""
CFA Prep CLI - Tests for the progress tracker module
Author: CodeBuddy AI Assistant
Purpose: Check the progress tracker: the mastered and fuzzy topics of the current level.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.progress_tracker import ProgressTracker


def test_progress_tracker():
    """Test the progress tracker stores and retrieves JSON data"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            tracker = ProgressTracker()
            # Fresh load returns default structure
            data = tracker.load()
            assert "mastered" in data
            assert "fuzzy" in data
            assert data["mastered"] == []
            assert data["fuzzy"] == []
            # Update with entries
            tracker.update(mastered=["[Econ > Module 1] Topic A"], fuzzy=["[Econ > Module 2] Topic B"])
            loaded = tracker.load()
            assert loaded["mastered"] == ["[Econ > Module 1] Topic A"]
            assert loaded["fuzzy"] == ["[Econ > Module 2] Topic B"]
            # Deduplication
            tracker.update(mastered=["[Econ > Module 1] Topic A"])
            assert len(tracker.load()["mastered"]) == 1
            # Remove entries
            _ = tracker.remove_entries({0, 1})
            assert tracker.load()["mastered"] == []
            assert tracker.load()["fuzzy"] == []
            # get_key_points_to_review returns fuzzy only
            tracker.update(fuzzy=["[Econ > Module 2] Topic B"])
            assert tracker.get_key_points_to_review() == ["[Econ > Module 2] Topic B"]
            print("  ✅ Progress tracker is fine")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)
