"""
CFA Prep CLI - Tests for the images module
Author: CodeBuddy AI Assistant
Purpose: Check the helpers that keep the picture of a flashcard: copying it into
         the data root, cleaning a pasted path and opening it in the viewer.
"""

import os
import sys
from pathlib import Path
from unittest import mock

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.images import (
    attach_image,
    clean_pasted_path,
    image_lines,
    open_externally,
)


def test_clean_pasted_path():
    """Test that a pasted path is cleaned"""
    assert clean_pasted_path('"C:\\Users\\test\\pic.png"') == "C:\\Users\\test\\pic.png"
    assert clean_pasted_path("C:\\\\Users\\\\test\\\\pic.png") == "C:\\Users\\test\\pic.png"
    # The separators of the platform are used
    expected = "\\tmp\\pic.png" if os.name == "nt" else "/tmp/pic.png"
    assert clean_pasted_path("  /tmp/pic.png  ") == expected
    print("  ✅ A pasted path is cleaned")


def test_attach_image():
    """Test that the picture is copied into the images folder"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "diagram.png"
        _ = source.write_bytes(b"\x89PNG\r\n\x1a\n")
        images_dir = root / "flashcards" / "images"

        relative = attach_image(source, images_dir)
        assert relative.startswith("images/"), relative
        assert relative.endswith(".png"), relative
        copied = root / "flashcards" / relative
        assert copied.is_file()
        assert copied.read_bytes() == source.read_bytes()

        # Attaching the same file again reuses the copy
        again = attach_image(source, images_dir)
        assert again == relative
    print("  ✅ The picture is copied into the images folder")


def test_attach_image_refuses_bad_files():
    """Test that a missing, empty or unsupported file is refused"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        images_dir = root / "images"

        empty = root / "empty.png"
        _ = empty.write_bytes(b"")
        unsupported = root / "notes.txt"
        _ = unsupported.write_bytes(b"hello")

        for bad in (root / "missing.png", empty, unsupported):
            try:
                _ = attach_image(bad, images_dir)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{bad.name} must be refused")
    print("  ✅ A missing, empty or unsupported file is refused")


def test_open_externally():
    """Test that the picture is handed over to the system viewer"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "pic.png"
        _ = target.write_bytes(b"\x89PNG\r\n\x1a\n")

        with (
            mock.patch("cfa_prep.images.os.startfile", create=True) as startfile,
            mock.patch("cfa_prep.images.os.name", "nt"),
        ):
            assert open_externally(target) is True
            startfile.assert_called_once()

        # A viewer that cannot be started is reported
        with (
            mock.patch("cfa_prep.images.os.startfile", create=True) as startfile,
            mock.patch("cfa_prep.images.os.name", "nt"),
        ):
            startfile.side_effect = OSError("no viewer")
            assert open_externally(target) is False
    print("  ✅ The picture is handed over to the system viewer")


def test_image_lines():
    """Test the lines that describe the picture of a card"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "images" / "pic.png"
        lines = image_lines(target, "Spot vs forward curve")
        text = "\n".join(lines)
        assert "pic.png" in text
        assert "Spot vs forward curve" in text
        assert "'o'" in text

        # Without a caption the hint is still there
        plain = "\n".join(image_lines(target))
        assert "'o'" in plain
    print("  ✅ The lines that describe the picture of a card")
