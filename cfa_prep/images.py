"""
CFA Prep CLI - Image module
Author: CodeBuddy AI Assistant
Purpose: Keep the picture of a flashcard: copy it into the data root and open it
         in the image viewer of the system.  A picture is never redrawn in the
         terminal - a drawing of a diagram is not reliable enough to study from,
         so the original file is shown instead.
"""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def clean_pasted_path(text: str) -> str:
    """Clean a path that was pasted (Windows Terminal quotes and escapes it)."""
    path = text.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in "\"'":
        path = path[1:-1]
    path = path.replace("\\\\", "\\")
    if os.name == "nt":
        path = path.replace("/", "\\")
    return path.strip()


def attach_image(source: Path, images_dir: Path) -> str:
    """
    Copy the image into the images folder of the data root and return its path
    relative to the flashcards folder (for example "images/9f2c1a7b.png").
    """
    if not source.is_file():
        raise ValueError(f"not a file: {source}")
    suffix = source.suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        allowed = ", ".join(sorted(IMAGE_SUFFIXES))
        raise ValueError(f"unsupported picture type '{suffix or '?'}' (allowed: {allowed})")
    size = source.stat().st_size
    if size == 0:
        raise ValueError("the file is empty")
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"the file is too large ({size // (1024 * 1024)} MB, max 10 MB)")
    digest = hashlib.sha1(source.read_bytes()).hexdigest()[:16]
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / f"{digest}{suffix}"
    if not target.exists():
        _ = shutil.copy2(source, target)
    return f"images/{target.name}"


def open_externally(path: Path) -> bool:
    """Open the image in the default viewer of the system."""
    try:
        if os.name == "nt" and hasattr(os, "startfile"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            _ = subprocess.Popen(["open", str(path)])
        else:
            _ = subprocess.Popen(["xdg-open", str(path)])
        return True
    except OSError:
        return False


def image_lines(path: Path, caption: str = "") -> list[str]:
    """
    Return the lines that tell where the picture is and how to open it.

    A picture that is not on the disk any more gets no hint: there is nothing
    to open, so the option is not offered either.
    """
    if not path.is_file():
        return [f"     ⚠️  {path} (not found)"]
    lines = [f"     📁 {path}"]
    if caption:
        lines.append(f"     🖼️  {caption}")
    lines.append("     (press 'o' to open it in the image viewer)")
    return lines
