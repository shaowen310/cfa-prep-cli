# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Knowledge base management module
Author: CodeBuddy AI Assistant
Purpose: Read TXT knowledge files under data/kb/, split them into pages, and support keyword search (regex + fuzzy matching).
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .utils import (
    get_data_dir,
    fuzzy_match,
    extract_context,
    read_file_text,
)


class KnowledgeBase:
    """
    CFA knowledge base manager.
    Scans .txt files under data/kb/,
    splits pages using the "===== PAGE N =====" marker,
    and provides keyword search functionality.
    """

    def __init__(self):
        self.kb_dir = get_data_dir("kb")
        # Cache: {file path: {page number: page text}}
        self._cache: Dict[str, Dict[int, str]] = {}

    def scan_files(self) -> List[Path]:
        """Scan all .txt files under data/kb/"""
        return sorted(self.kb_dir.glob("*.txt"))

    def load_file(self, filepath: Path) -> Dict[int, str]:
        """
        Load a single knowledge file, split by page number.
        Returns a {page number: page text} dict.
        Page marker format: ===== PAGE N =====
        """
        if str(filepath) in self._cache:
            return self._cache[str(filepath)]

        text = read_file_text(filepath)
        pages: Dict[int, str] = {}

        # Split by ===== PAGE N =====
        # Use regex to match the page marker
        pattern = r"^=====\s*PAGE\s+(\d+)\s*=====\s*$"
        parts = re.split(pattern, text, flags=re.MULTILINE)

        # parts[0] is the content before the first page marker (if any)
        # Then it is (page1, content1, page2, content2, ...)
        if len(parts) > 1:
            # Skip parts[0] (content before the first marker, if any)
            start = 0
            if not re.match(pattern, parts[0].strip(), re.MULTILINE):
                # parts[0] is content before the marker; treat it as page 0
                if parts[0].strip():
                    pages[0] = parts[0].strip()
                start = 1

            for i in range(start, len(parts) - 1, 2):
                try:
                    page_num = int(parts[i])
                    page_text = parts[i + 1].strip()
                    if page_text:
                        pages[page_num] = page_text
                except (ValueError, IndexError):
                    continue
        else:
            # No page markers; treat the whole file as a single page
            pages[1] = text.strip()

        self._cache[str(filepath)] = pages
        return pages

    def load_all(self) -> Dict[str, Dict[int, str]]:
        """Load all knowledge files"""
        result = {}
        for fp in self.scan_files():
            result[str(fp)] = self.load_file(fp)
        return result

    def search(
        self,
        keyword: str,
        use_regex: bool = False,
        use_fuzzy: bool = True,
        max_results: int = 10,
    ) -> List[Dict[str, any]]:
        """
        Search for a keyword across all knowledge files.

        Parameters:
            keyword: the search keyword
            use_regex: whether to search using regular expressions
            use_fuzzy: whether to enable fuzzy matching (approximate spelling)
            max_results: maximum number of results to return

        Returns:
            a list of {file, page, snippet} dicts
        """
        results = []
        all_data = self.load_all()

        for filepath, pages in all_data.items():
            fname = os.path.basename(filepath)
            for page_num, page_text in pages.items():
                matched = False
                snippet = ""

                if use_regex:
                    try:
                        if re.search(keyword, page_text, re.IGNORECASE):
                            matched = True
                            snippet = extract_context(page_text, keyword)
                    except re.error:
                        # Invalid regex; fall back to normal search
                        pass

                if not matched and use_fuzzy:
                    # First try exact containment matching
                    if keyword.lower() in page_text.lower():
                        matched = True
                        snippet = extract_context(page_text, keyword)
                    # Then try fuzzy matching
                    elif fuzzy_match(keyword, page_text):
                        matched = True
                        snippet = extract_context(page_text, keyword)

                if not matched:
                    # Plain containment matching
                    if keyword.lower() in page_text.lower():
                        matched = True
                        snippet = extract_context(page_text, keyword)

                if matched:
                    results.append({
                        "file": fname,
                        "filepath": filepath,
                        "page": page_num,
                        "snippet": snippet,
                    })

                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break

        return results[:max_results]

    def get_stats(self) -> Dict[str, any]:
        """Return knowledge base statistics"""
        files = self.scan_files()
        total_pages = 0
        file_stats = []

        for fp in files:
            pages = self.load_file(fp)
            total_pages += len(pages)
            file_stats.append({
                "name": fp.name,
                "pages": len(pages),
            })

        return {
            "total_files": len(files),
            "total_pages": total_pages,
            "files": file_stats,
        }

    def clear_cache(self) -> None:
        """Clear the cache"""
        self._cache.clear()
