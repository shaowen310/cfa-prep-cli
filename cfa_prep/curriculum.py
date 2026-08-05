# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Curriculum module
Author: CodeBuddy AI Assistant
Purpose: Provide a single source of truth for the CFA exam curriculum (subjects + topics)
         per level, stored at <data_root>/curriculum.json. Powers quiz topic selection,
         input auto-correction, and progress coverage tracking.

The scaffold is generated from the publicly published CFA topic structure
(10 topic areas + typical sub-topics per level). It is factual structure, not
reproduced copyrighted text. Users may replace it via `curriculum import`.
"""

import json
from pathlib import Path

from .utils import get_data_root, load_json, save_json, fuzzy_match

# Official CFA topic area names (public, non-copyrighted structure)
CANONICAL_SUBJECTS = [
    "Ethical & Professional Standards",
    "Quantitative Methods",
    "Economics",
    "Financial Statement Analysis",
    "Corporate Issuers",
    "Equity Investments",
    "Fixed Income",
    "Derivatives",
    "Alternative Investments",
    "Portfolio Management",
]

# Convenience aliases mapping to canonical subject names, used by normalize_subject.
# e.g. "FRA" / "fra" / "financial reporting" -> "Financial Statement Analysis"
SUBJECT_ALIASES = {
    "fra": "Financial Statement Analysis",
    "financial statement analysis": "Financial Statement Analysis",
    "financial reporting": "Financial Statement Analysis",
    "financial reporting analysis": "Financial Statement Analysis",
    "fsa": "Financial Statement Analysis",
    "fina": "Financial Statement Analysis",
    "quant": "Quantitative Methods",
    "quantitative methods": "Quantitative Methods",
    "qm": "Quantitative Methods",
    "econ": "Economics",
    "economics": "Economics",
    "fixed income": "Fixed Income",
    "fi": "Fixed Income",
    "fixed": "Fixed Income",
    "equity": "Equity Investments",
    "equity investments": "Equity Investments",
    "eq": "Equity Investments",
    "derivatives": "Derivatives",
    "deriv": "Derivatives",
    "derivs": "Derivatives",
    "alt": "Alternative Investments",
    "alternative investments": "Alternative Investments",
    "alternatives": "Alternative Investments",
    "portfolio": "Portfolio Management",
    "portfolio management": "Portfolio Management",
    "pm": "Portfolio Management",
    "corp finance": "Corporate Issuers",
    "corporate finance": "Corporate Issuers",
    "corporate issuers": "Corporate Issuers",
    "corporate": "Corporate Issuers",
    "corp": "Corporate Issuers",
    "ethics": "Ethical & Professional Standards",
    "ethical & professional standards": "Ethical & Professional Standards",
    "professional standards": "Ethical & Professional Standards",
    "et&ps": "Ethical & Professional Standards",
}

# Default scaffold keyed by level. Subjects use the canonical names above.
# Sub-topics are typical topics from the publicly published Candidate Body of
# Knowledge; edit freely after import.
DEFAULT_CURRICULUM = {
    "L1": {
        "Ethical & Professional Standards": [
            "CFA Institute Code of Ethics",
            "Standards of Professional Conduct (I-VII)",
            "GIPS compliance overview",
            "Global Investment Performance Standards",
        ],
        "Quantitative Methods": [
            "Time value of money",
            "Probability concepts",
            "Common probability distributions",
            "Sampling and estimation",
            "Hypothesis testing",
            "Introduction to linear regression",
            "Time-series analysis basics",
        ],
        "Economics": [
            "Demand and supply analysis",
            "Consumer and producer theory",
            "Firm and market structures",
            "Monetary and fiscal policy",
            "International trade and capital flows",
            "Exchange rate determination",
            "Economic growth",
            "Business cycle analysis",
        ],
        "Financial Statement Analysis": [
            "Introduction to financial statement analysis",
            "Financial reporting standards",
            "Understanding the income statement",
            "Understanding the balance sheet",
            "Understanding the cash flow statement",
            "Financial analysis techniques (ratios)",
            "Inventories",
            "Long-lived assets",
            "Income taxes",
            "Non-current liabilities (leases, debt)",
            "Financial reporting quality",
        ],
        "Corporate Issuers": [
            "Corporate governance",
            "Capital budgeting",
            "Cost of capital",
            "Measures of leverage",
            "Working capital management",
            "Introduction to corporate finance (financing)",
        ],
        "Equity Investments": [
            "Market organization and structure",
            "Security market indices",
            "Market efficiency",
            "Overview of equity securities",
            "Introduction to industry and company analysis",
            "Equity valuation concepts",
        ],
        "Fixed Income": [
            "Fixed-income securities definitions",
            "Fixed-income markets",
            "Introduction to fixed-income valuation",
            "Term structure of interest rates",
            "Introduction to asset-backed securities",
            "Understanding fixed-income risk and return",
            "Credit risk basics",
        ],
        "Derivatives": [
            "Derivative markets and instruments",
            "Basics of derivative pricing",
            "Options basics",
            "Forward and futures basics",
            "Swap basics",
        ],
        "Alternative Investments": [
            "Alternative investments overview",
            "Hedge funds",
            "Private equity",
            "Real estate",
            "Commodities",
        ],
        "Portfolio Management": [
            "Portfolio management: an overview",
            "Portfolio risk and return: Part I & II",
            "Behavioral finance",
            "Introduction to risk management",
            "Technical analysis",
            "Introduction to asset allocation",
        ],
    },
    "L2": {
        "Ethical & Professional Standards": [
            "Code of Ethics and Standards application",
            "GIPS: composite construction",
            "Asset manager code of professional conduct",
        ],
        "Quantitative Methods": [
            "Multiple regression",
            "Time-series analysis",
            "Machine learning basics",
            "Probability, decision analysis, and simulation",
            "Big data and FinTech",
        ],
        "Economics": [
            "Currency exchange rate forecasting",
            "Economic growth and investment decision",
            "Economics of regulation",
        ],
        "Financial Statement Analysis": [
            "Intercorporate investments",
            "Employee compensation (pensions, share-based)",
            "Multinational operations (FX effects)",
            "Analysis of financial institutions",
            "Evaluating financial reporting quality",
            "Analysis of inventory and long-lived assets",
        ],
        "Corporate Issuers": [
            "Capital structure and company analysis",
            "Corporate governance and ESG",
            "Cost of capital: advanced",
            "Mergers and acquisitions",
            "Dividend policy and share repurchases",
        ],
        "Equity Investments": [
            "Equity valuation: applications",
            "Free cash flow valuation (FCFF/FCFE)",
            "Market-based valuation (multiples)",
            "Residual income valuation",
            "Private company valuation",
        ],
        "Fixed Income": [
            "Fixed-income valuation: analysis of bonds",
            "Term structure and yield spreads",
            "Fixed-income risk and return",
            "Credit analysis models",
            "Asset-backed securities",
            "Fixed-income portfolio management basics",
        ],
        "Derivatives": [
            "Option valuation (binomial, Black-Scholes)",
            "Forward and futures valuation",
            "Swap valuation",
            "Credit derivatives",
        ],
        "Alternative Investments": [
            "Alternative investments: private equity",
            "Real estate investments",
            "Hedge fund strategies and valuation",
            "Commodities and other alternatives",
        ],
        "Portfolio Management": [
            "Portfolio concepts: mean-variance analysis",
            "Asset allocation strategies",
            "Fixed-income and equity portfolio management",
            "Derivatives in portfolio management",
            "Alternative investments in portfolios",
        ],
    },
    "L3": {
        "Ethical & Professional Standards": [
            "Ethics application in portfolio management",
            "GIPS for asset owners and firms",
            "CFA Institute guidance for standards",
        ],
        "Quantitative Methods": [
            "Portfolio risk and return measurement",
            "Trade strategy and execution analytics",
            "Performance evaluation",
        ],
        "Economics": [
            "Capital market expectations",
            "Economic and capital market cycles",
            "Currency management",
        ],
        "Financial Statement Analysis": [
            "Financial analysis in portfolio context",
            "Multi-currency accounting decisions",
            "ESG considerations in analysis",
        ],
        "Corporate Issuers": [
            "Capital structure policy",
            "Dividend and share repurchase policy",
            "Corporate restructuring",
        ],
        "Equity Investments": [
            "Equity portfolio management",
            "Passive vs active equity strategies",
            "Equity manager selection and evaluation",
        ],
        "Fixed Income": [
            "Fixed-income portfolio management: liability-driven",
            "Yield curve strategies",
            "Credit strategies in fixed income",
            "Global fixed-income investing",
            "Fixed-income performance evaluation",
        ],
        "Derivatives": [
            "Risk management using derivatives",
            "Options strategies for portfolios",
            "Futures and swaps in portfolio management",
        ],
        "Alternative Investments": [
            "Alternative investments portfolio construction",
            "Due diligence of alternative investments",
            "Risk and return of alternative assets",
        ],
        "Portfolio Management": [
            "Asset allocation",
            "Portfolio construction and monitoring",
            "Rebalancing and performance attribution",
            "Behavioral finance in practice",
            "Risk governance",
        ],
    },
}


class Curriculum:
    """
    Load / save / query the CFA curriculum.

    Stored as <data_root>/curriculum.json with shape:
        {
            "L1": {"<Subject>": ["<Topic>", ...], ...},
            "L2": {...},
            "L3": {...}
        }
    """

    def __init__(self):
        self.path: Path = get_data_root() / "curriculum.json"

    # --- persistence -------------------------------------------------------

    def load(self) -> dict[str, dict[str, list[str]]]:
        """Load the curriculum, returning the DEFAULT scaffold if no file exists yet."""
        data = load_json(self.path)
        if not data:
            return DEFAULT_CURRICULUM
        return data

    def save(self, data: dict[str, dict[str, list[str]]]) -> None:
        """Write the curriculum data to curriculum.json."""
        save_json(self.path, data)

    def seed(self) -> bool:
        """
        Write the DEFAULT scaffold if no curriculum file exists yet (idempotent).
        Returns True if a file was written, False if one already existed.
        """
        if self.path.exists():
            return False
        self.save(DEFAULT_CURRICULUM)
        return True

    def import_file(self, filepath: str) -> None:
        """
        Replace the curriculum from a user-provided JSON file.
        Validates the structure: dict of levels -> dict of subjects -> list of topics.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Curriculum file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Curriculum file must be a JSON object mapping level -> subject -> topics")

        # Normalize / validate structure
        cleaned: dict[str, dict[str, list[str]]] = {}
        for level, subjects in data.items():
            if not isinstance(subjects, dict):
                raise ValueError(f"Level {level!r} must map to a dictionary of subjects")
            level_key = str(level).upper()
            cleaned[level_key] = {}
            for subject, topics in subjects.items():
                if not isinstance(topics, list):
                    raise ValueError(f"Subject {subject!r} in {level_key} must map to a list of topics")
                cleaned[level_key][str(subject)] = [str(t) for t in topics]

        self.save(cleaned)

    # --- queries -----------------------------------------------------------

    def levels(self) -> list[str]:
        """Return the available levels (e.g. ['L1', 'L2', 'L3'])."""
        return list(self.load().keys())

    def all_subjects(self, level: str = "L1") -> list[str]:
        """Return the list of subjects for a given level (fallback to scaffold)."""
        data = self.load()
        return list(data.get(level.upper(), {}).keys())

    def all_topics(self, level: str = "L1") -> list[str]:
        """
        Return all topics across all subjects for a level, flattened as
        "[Subject] Topic" strings (same format the quiz engine uses).
        """
        data = self.load()
        subjects = data.get(level.upper(), {})
        topics: list[str] = []
        for subject, topic_list in subjects.items():
            for topic in topic_list:
                topics.append(f"[{subject}] {topic}")
        return topics

    def count_topics(self, level: str = "L1") -> int:
        """Return the total number of topics for a level."""
        data = self.load()
        subjects = data.get(level.upper(), {})
        return sum(len(t) for t in subjects.values())

    def find_topic(self, level: str, subject: str, topic: str) -> str | None:
        """Look up a topic within a subject; returns the exact topic string or None."""
        data = self.load()
        topics = data.get(level.upper(), {}).get(subject, [])
        norm = topic.strip().lower()
        for t in topics:
            if t.strip().lower() == norm:
                return t
        return None

    # --- input correction ---------------------------------------------------

    def normalize_subject(self, text: str, level: str = "L1") -> str | None:
        """
        Correct / normalize a typed subject name to a canonical curriculum subject.

        Rules (highest priority first):
          1. Exact (case-insensitive) match against a canonical subject name.
          2. Exact match against a known alias (e.g. "FRA" -> "Financial Statement Analysis").
          3. Fuzzy match (subsequence) against a canonical subject name.

        Returns the canonical subject name, or None if no confident match.
        """
        cleaned = text.strip().lower()
        if not cleaned:
            return None

        subjects = self.all_subjects(level)

        # 1. exact canonical match
        for s in subjects:
            if s.lower() == cleaned:
                return s

        # 2. alias match
        if cleaned in SUBJECT_ALIASES:
            return SUBJECT_ALIASES[cleaned]

        # 3. fuzzy (subsequence) match against canonical names
        candidates = [s for s in subjects if fuzzy_match(cleaned, s)]
        if len(candidates) == 1:
            return candidates[0]

        return None

    def normalize_topic(self, text: str, subject: str, level: str = "L1") -> str | None:
        """
        Correct / normalize a typed topic against the curriculum for a subject.

        Returns the exact curriculum topic string, or None if no confident match.
        """
        cleaned = text.strip().lower()
        if not cleaned:
            return None

        data = self.load()
        topics = data.get(level.upper(), {}).get(subject, [])

        # exact match
        for t in topics:
            if t.lower() == cleaned:
                return t

        # fuzzy (subsequence) match
        candidates = [t for t in topics if fuzzy_match(cleaned, t)]
        if len(candidates) == 1:
            return candidates[0]

        return None
