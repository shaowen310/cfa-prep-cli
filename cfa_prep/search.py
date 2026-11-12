# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Unified search module
Author: CodeBuddy AI Assistant
Purpose: Look a keyword up in every source the user has written: the knowledge
         base (data/kb/*.txt), the manual flashcards and the mistake log.
         Every hit is tagged with the source it came from.
"""

import re
from typing import TypedDict

from .flashcard_generator import FlashcardGenerator
from .knowledge_base import KnowledgeBase
from .mistake_analyzer import MistakeAnalyzer
from .utils import contains_word, extract_context, fuzzy_word_match

# Source tags used in a hit
SOURCE_KB = "kb"
SOURCE_FLASHCARD = "flashcard"
SOURCE_MISTAKE = "mistake"

# Icons shown in the CLI output
SOURCE_ICONS = {
    SOURCE_KB: "📄",
    SOURCE_FLASHCARD: "🗂️",
    SOURCE_MISTAKE: "❌",
}

# What extract_context returns when it cannot locate the keyword
NO_CONTEXT = "(No matching content found)"


class SearchHit(TypedDict):
    """A single search hit, tagged with the source it came from."""
    source: str      # "kb" | "flashcard" | "mistake"
    title: str       # file name / card question / mistake question
    location: str    # "page 12" / "Economics > Module 3: Fiscal Policy"
    snippet: str     # the matched text


class SearchOutcome(TypedDict):
    """The hits of a search plus the size of every searched source."""
    hits: list[SearchHit]
    kb_files: int
    kb_pages: int
    flashcards: int
    mistakes: int


def _is_match(text: str, keyword: str, use_regex: bool, use_fuzzy: bool) -> bool:
    """
    Return True when the keyword is found in the text.

    A regex is tried first (when enabled), then the keyword as a whole word, then
    a fuzzy match against the words of the text.  An invalid regex falls back to
    the whole-word search.
    """
    if use_regex:
        try:
            if re.search(keyword, text, re.IGNORECASE):
                return True
        except re.error:
            pass
    if contains_word(text, keyword):
        return True
    return bool(use_fuzzy) and fuzzy_word_match(text, keyword)


def _snippet(text: str, keyword: str, use_regex: bool) -> str:
    """Return the context around the match."""
    if use_regex:
        try:
            match = re.search(keyword, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                snippet = text[start:end].strip()
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                return snippet
        except re.error:
            pass
    snippet = extract_context(text, keyword)
    if snippet == NO_CONTEXT:
        # A fuzzy hit can span the whole text; show its beginning instead.
        return text[:160].strip() + ("..." if len(text) > 160 else "")
    return snippet


def _search_kb(
    keyword: str, use_regex: bool, use_fuzzy: bool, limit: int
) -> list[SearchHit]:
    """Search the .txt files under data/kb/."""
    kb = KnowledgeBase()
    hits: list[SearchHit] = []
    for r in kb.search(
        keyword=keyword,
        use_regex=use_regex,
        use_fuzzy=use_fuzzy,
        max_results=limit,
    ):
        hits.append({
            "source": SOURCE_KB,
            "title": r["file"],
            "location": f"page {r['page']}",
            "snippet": r["snippet"],
        })
    return hits


def _search_flashcards(
    keyword: str, use_regex: bool, use_fuzzy: bool, limit: int
) -> list[SearchHit]:
    """Search the manual flashcards (question and answer)."""
    hits: list[SearchHit] = []
    for card in FlashcardGenerator().list_manual_cards():
        if len(hits) >= limit:
            break
        question = card.get("question", "")
        answer = card.get("answer", "")
        text = "\n".join(part for part in (question, answer) if part)
        if not text or not _is_match(text, keyword, use_regex, use_fuzzy):
            continue
        subject = card.get("subject", "")
        module = card.get("module", "")
        location = f"{subject} > {module}" if subject and module else (subject or module)
        hits.append({
            "source": SOURCE_FLASHCARD,
            "title": question,
            "location": location,
            "snippet": _snippet(text, keyword, use_regex),
        })
    return hits


def _search_mistakes(
    keyword: str, use_regex: bool, use_fuzzy: bool, limit: int
) -> list[SearchHit]:
    """Search the mistake log (question, options and explanation)."""
    hits: list[SearchHit] = []
    for record in MistakeAnalyzer().all_mistakes():
        if len(hits) >= limit:
            break
        question = record.get("question", "")
        options = record.get("options", []) or []
        explanation = record.get("explanation", "")
        text = "\n".join(
            part for part in ([question, *options, explanation]) if part
        )
        if not text or not _is_match(text, keyword, use_regex, use_fuzzy):
            continue
        subject = record.get("subject", "")
        module = record.get("module", "")
        location = f"{subject} > {module}" if subject and module else (subject or module)
        hits.append({
            "source": SOURCE_MISTAKE,
            "title": question,
            "location": location,
            "snippet": _snippet(text, keyword, use_regex),
        })
    return hits


def search_all(
    keyword: str,
    use_regex: bool = False,
    use_fuzzy: bool = True,
    max_results: int = 10,
) -> SearchOutcome:
    """
    Search every source for the keyword.

    `max_results` caps the hits of each source, so one source cannot hide the
    others.  The hits come back grouped by source: knowledge base first, then
    the flashcards, then the mistake log.
    """
    kb = KnowledgeBase()
    stats = kb.get_stats()
    cards = FlashcardGenerator().list_manual_cards()
    records = MistakeAnalyzer().all_mistakes()

    hits: list[SearchHit] = []
    hits.extend(_search_kb(keyword, use_regex, use_fuzzy, max_results))
    hits.extend(_search_flashcards(keyword, use_regex, use_fuzzy, max_results))
    hits.extend(_search_mistakes(keyword, use_regex, use_fuzzy, max_results))

    return {
        "hits": hits,
        "kb_files": stats["total_files"],
        "kb_pages": stats["total_pages"],
        "flashcards": len(cards),
        "mistakes": len(records),
    }
