# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Curriculum module
Author: CodeBuddy AI Assistant
Purpose: Provide a single source of truth for the CFA exam curriculum (subjects + topics)
         per level, stored at <data_root>/curriculum.json. Powers quiz topic selection,
         input auto-correction, and progress coverage tracking.

The curriculum is user-supplied via `curriculum import` — there is no bundled default
scaffold. Imported curriculum text is provided by the user and should respect the
copyright of its source (e.g. the CFA Institute).
"""

import json
from pathlib import Path

from .utils import get_data_dir, load_json, save_json, fuzzy_match

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


class Curriculum:
    """
    Load / save / query the CFA curriculum.

    Stored as <data_root>/kb/curriculum.json with shape:
        {
            "L1": {
                "<Subject>": {
                    "<Module>": ["<Topic>", ...],
                    ...
                },
                ...
            },
            "L2": {...},
            "L3": {...}
        }

    Modules are first-class: every subject maps to a dict of modules, each of which
    maps to a list of topics. A subject imported as a flat list of topics is wrapped
    under a default module ("General") so the model stays consistent.

    The curriculum is populated by the user via `import_file`; an empty / missing
    file is treated as an empty curriculum.
    """

    # Default module name used when a subject is provided as a flat list of topics.
    DEFAULT_MODULE: str = "General"

    def __init__(self):
        self.path: Path = get_data_dir("kb") / "curriculum.json"

    # --- persistence -------------------------------------------------------

    def load(self) -> dict[str, dict[str, dict[str, list[str]]]]:
        """Load the curriculum, returning an empty dict if no file exists yet."""
        data = load_json(self.path)
        if not data:
            return {}
        return data

    def save(self, data: dict[str, dict[str, dict[str, list[str]]]]) -> None:
        """Write the curriculum data to curriculum.json."""
        save_json(self.path, data)

    def seed(self) -> bool:
        """
        Create an empty curriculum file if none exists yet (idempotent).
        Returns True if a file was written, False if one already existed.
        """
        if self.path.exists():
            return False
        self.save({})
        return True

    def import_file(self, filepath: str) -> None:
        """
        Replace the curriculum from a user-provided JSON file.
        Validates the structure: dict of levels -> dict of subjects -> modules/topics.

        Subject shapes accepted (all normalized to the nested module form):
          * {"Subject": ["Topic", ...]}               -> wrapped under "General"
          * {"Subject": {"Module": ["Topic", ...]}}   -> kept as-is (modules preserved)
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Curriculum file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Curriculum file must be a JSON object mapping level -> subject -> topics")

        # Normalize / validate structure
        cleaned: dict[str, dict[str, dict[str, list[str]]]] = {}
        for level, subjects in data.items():
            if not isinstance(subjects, dict):
                raise ValueError(f"Level {level!r} must map to a dictionary of subjects")
            level_key = str(level).upper()
            cleaned[level_key] = {}
            for subject, value in subjects.items():
                cleaned[level_key][str(subject)] = self._normalize_modules(value, subject, level_key)

        self.save(cleaned)

    @staticmethod
    def _normalize_modules(value, subject: str, level_key: str) -> dict[str, list[str]]:
        """
        Normalize a subject's topic definition into the nested "module -> [topics]" form.

        Supports:
          * a list of topic strings   -> wrapped under Curriculum.DEFAULT_MODULE
          * a dict of modules         -> kept as-is, each module validated as a list of topics
        """
        if isinstance(value, list):
            return {Curriculum.DEFAULT_MODULE: [str(t) for t in value]}

        if isinstance(value, dict):
            modules: dict[str, list[str]] = {}
            for module, items in value.items():
                if not isinstance(items, list):
                    raise ValueError(
                        f"Module {module!r} in {level_key} / {subject!r} must map to a list of topics"
                    )
                modules[str(module)] = [str(item) for item in items]
            return modules

        raise ValueError(
            f"Subject {subject!r} in {level_key} must map to a list of topics or a dict of modules"
        )

    # --- queries -----------------------------------------------------------

    def levels(self) -> list[str]:
        """Return the available levels (e.g. ['L1', 'L2', 'L3'])."""
        return list(self.load().keys())

    def all_subjects(self, level: str = "L1") -> list[str]:
        """Return the list of subjects for a given level."""
        data = self.load()
        return list(data.get(level.upper(), {}).keys())

    def subject_modules(self, level: str = "L1", subject: str = "") -> dict[str, list[str]]:
        """Return the {module: [topics]} dict for a subject, or {} if absent."""
        if not subject:
            return {}
        data = self.load()
        return data.get(level.upper(), {}).get(subject, {})

    def all_modules(self, level: str = "L1", subject: str = "") -> list[str]:
        """Return the module names for a subject (or across all subjects if none given)."""
        data = self.load()
        if subject:
            return list(data.get(level.upper(), {}).get(subject, {}).keys())
        modules: list[str] = []
        for subj in data.get(level.upper(), {}).values():
            modules.extend(subj.keys())
        return modules

    def all_topics(self, level: str = "L1") -> list[str]:
        """
        Return all topics for a level, flattened as "[Subject > Module] Topic" strings.
        The module layer is preserved in each label so quiz / progress can track per-module.
        """
        data = self.load()
        subjects = data.get(level.upper(), {})
        topics: list[str] = []
        for subject, modules in subjects.items():
            for module, module_topics in modules.items():
                for topic in module_topics:
                    topics.append(f"[{subject} > {module}] {topic}")
        return topics

    def count_topics(self, level: str = "L1") -> int:
        """Return the total number of topics for a level."""
        data = self.load()
        subjects = data.get(level.upper(), {})
        return sum(len(t) for m in subjects.values() for t in m.values())

    def find_topic(self, level: str, subject: str, topic: str) -> str | None:
        """Look up a topic within a subject (searching all its modules); exact match or None."""
        modules = self.subject_modules(level, subject)
        norm = topic.strip().lower()
        for module_topics in modules.values():
            for t in module_topics:
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
        Correct / normalize a typed topic against the curriculum for a subject,
        searching across all of the subject's modules.

        Returns the exact curriculum topic string, or None if no confident match.
        """
        cleaned = text.strip().lower()
        if not cleaned:
            return None

        modules = self.subject_modules(level, subject)
        all_topics: list[str] = [t for ts in modules.values() for t in ts]

        # exact match
        for t in all_topics:
            if t.lower() == cleaned:
                return t

        # fuzzy (subsequence) match
        candidates = [t for t in all_topics if fuzzy_match(cleaned, t)]
        if len(candidates) == 1:
            return candidates[0]

        return None
