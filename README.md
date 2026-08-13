# CFA Prep CLI

> CFA exam prep CLI tool — knowledge base search · smart quizzing · mistake analysis · progress tracking · flashcards · IPS templates

## Overview

CFA Prep CLI is a pure-Python command-line CFA study assistant covering all preparation needs for Levels I / II / III. It requires no third-party dependencies and works out of the box.

### Core Features

| Feature            | Description                                                        |
| ------------------ | ----------------------------------------------------------------- |
| **Knowledge Search** | Search keywords across textbook/Notes slices, with regex and fuzzy matching |
| **Smart Quiz**      | L1 mixed selection / L2 vignette / L3 scenario analysis, with mistake-priority questions |
| **Mistake Analysis** | Auto-classifies error causes (concept confusion / calculation error / misreading), generates review suggestions |
| **Progress Tracking** | Maintains a study progress file, tracks mastered and fuzzy knowledge points |
| **Flashcards** | Manually add Q&A flashcards, selecting the subject/module from the curriculum |
| **IPS Templates**    | L3 personal and institutional IPS templates with full frameworks |

## Quick Start

### 1. Install as `cfa-prep`

Install the package with pip so the `cfa-prep` command is available from anywhere:

```bash
pip install .
```

> For development, use an editable install so code changes take effect immediately:
> `pip install -e .`

Or use the one-click setup script for your platform (installs the package, then initializes):

```bash
# Linux/macOS
./setup.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File setup.ps1
```

### 2. Initialize the data root

```bash
cfa-prep init
```

This creates all directories, config, progress file, and IPS templates.

### 3. Configure the data root

By default, all data is stored under `~/.cfa-prep`. You can relocate it in three ways (highest priority first):

| Method | Example |
| ------ | ------- |
| **`--home` flag** (per command) | `cfa-prep --home /path/to/data init` |
| **`CFA_PREP_HOME` env var** | `export CFA_PREP_HOME=/path/to/data` |
| **`data_root` in `settings.json`** | written automatically by `init` under `<data_root>/config/settings.json` |

The knowledge files live in the `kb/` subfolder of the data root:
- File name format: `l1_vol1_p1-60.txt`
- Mark pages inside files with `===== PAGE N =====`

### 4. Start using

```bash
cfa-prep search "FCFE"
```

## Command Reference

| Command                      | Description                  | Example                                        |
| ---------------------------- | ---------------------------- | ---------------------------------------------- |
| `init`                       | Initialize data root dirs and config | `cfa-prep init`                          |
| `home`                       | Show the data root directory path | `cfa-prep home`                    |
| `home --set <path>`          | Set the data root to an existing folder | `cfa-prep home --set D:\cfa\data` |
| `search <keyword>`           | Search the knowledge base    | `cfa-prep search "FCFE"`                       |
| `search --regex`             | Regex search                 | `cfa-prep search "FCF[EF]" --regex`            |
| `quiz --level L1`            | L1 quiz (10 mixed questions) | `cfa-prep quiz --level L1`                     |
| `quiz --level L2`            | L2 quiz (vignette)           | `cfa-prep quiz --level L2`                     |
| `quiz --level L3`            | L3 quiz (IPS scenario)       | `cfa-prep quiz --level L3`                     |
| `mistake -a`                 | Interactive mistake entry    | `cfa-prep mistake -a`                          |
| `recap`                      | View study progress          | `cfa-prep recap`                               |
| `recap --update`             | Update study progress        | `cfa-prep recap --update`                      |
| `recap --remove`             | Remove progress entries      | `cfa-prep recap --remove`                      |
| `flashcard --add`            | Manually add a flashcard (select subject/module from the curriculum) | `cfa-prep flashcard --add` |
| `flashcard -a`               | Shorthand for `--add`        | `cfa-prep flashcard -a`                       |
| `flashcard --review`         | Review cards (reveal answer or skip) | `cfa-prep flashcard --review`           |
| `flashcard -r`               | Shorthand for `--review`     | `cfa-prep flashcard -r`                       |
| `ips personal`               | Generate personal IPS template | `cfa-prep ips personal`                       |
| `ips inst`                   | Generate institutional IPS template | `cfa-prep ips inst`                     |
| `curriculum seed`            | Create an empty curriculum    | `cfa-prep curriculum seed`                   |
| `curriculum import <file>`   | Replace curriculum from a JSON file | `cfa-prep curriculum import my.json`   |
| `curriculum show`            | Display the current curriculum | `cfa-prep curriculum show`                   |

> All commands accept the global `--home PATH` flag, e.g. `cfa-prep --home ./my-data search "FCFE"`.

## Curriculum

The **curriculum** is the single source of truth for the subjects and topics you study
(per level L1/L2/L3). It drives quiz topic selection and (in a later pass) input
auto-correction and progress-coverage percentages.

There is **no bundled default scaffold** — the curriculum starts empty and is populated
by you via `cfa-prep curriculum import`. `cfa-prep init` only creates an empty
`curriculum.json`. Because actual CFA curriculum text is copyrighted by CFA Institute,
you should provide your own legally-owned material (your notes, the `kb/` text you
already own, or a topic list you export yourself).

The curriculum is stored at `<data_root>/kb/curriculum.json` with this shape — each subject
maps to one or more **modules**, and each module maps to a list of topics:

```json
{
  "L1": {
    "Financial Statement Analysis": {
      "Module 1: Analysis Framework": [
        "Introduction to financial statement analysis",
        "Financial reporting standards"
      ],
      "Module 2: The Financial Statements": [
        "Understanding the income statement",
        "Understanding the balance sheet"
      ]
    }
  }
}
```

A subject can also be provided as a plain list of topics — those get wrapped under a
default module named `General` automatically. Modules are first-class: the quiz draws
topics grouped by module, and progress can be tracked per-module.

### Commands

```bash
# Show the current curriculum
cfa-prep curriculum show

# Create an empty curriculum file (no-op if one already exists)
cfa-prep curriculum seed

# Replace the curriculum with your own JSON file
cfa-prep curriculum import /path/to/my-curriculum.json
```

The quiz engine draws its topic pool from the curriculum automatically — no other
configuration needed.

## Flashcards

Flashcards are created **manually** — there is no automatic Q&A extraction. Run the
interactive add flow, pick the **subject** and **module** from the curriculum, then
enter the front (question) and back (answer):

```bash
cfa-prep flashcard --add    # or: cfa-prep flashcard -a
```

- Leaving the subject blank **finishes** the session.
- After picking a subject you **must** pick a module to add a card (blank also finishes).
- The session reports how many flashcards were added, e.g. `Finished adding 2 flashcards.`

Cards are stored at `<data_root>/flashcards/flashcards.json`. You can add several cards
in one session — after saving one, the subject/module picker is shown again.

### Reviewing flashcards

Review the cards you've saved — see each question, reveal the answer, or skip to the
next card. **Running `flashcard` with no argument defaults to review** (use `--add`
to create cards instead):

```bash
cfa-prep flashcard             # review (default)
cfa-prep flashcard --review    # or: cfa-prep flashcard -r
```

You can optionally filter by **subject** (blank reviews all). For each card:

- `[Enter]` reveals the answer (then `[Enter]` moves on)
- `[n]` skips to the next card without revealing the answer
- `[b]` goes back to the previous card
- `[q]` quits the review

## Repository Layout

```
cfa-prep-cli/
├── README.md                    # This file
├── setup.sh                     # One-click setup script (Linux/macOS)
├── setup.ps1                    # One-click setup script (Windows/PowerShell)
├── pyproject.toml               # Packaging config (installs `cfa-prep` command)
├── .gitignore
├── cfa_prep/                    # The installable package
│   ├── __init__.py
│   ├── __main__.py              # enables `python -m cfa_prep`
│   ├── main.py                  # CLI entry point
│   ├── knowledge_base.py        # Knowledge base management
│   ├── quiz_engine.py           # Quiz engine
│   ├── mistake_analyzer.py      # Mistake analyzer
│   ├── progress_tracker.py      # Progress tracking
│   ├── flashcard_generator.py   # Manual flashcard management
│   ├── ips_builder.py           # IPS template building
│   ├── curriculum.py            # Curriculum module (subjects + topics per level)
│   └── utils.py                 # General utility functions (incl. data-root resolution)
└── tests/
    └── test_basic.py            # Basic tests
```

### Data Root Layout

Data files are stored under the configured data root (`~/.cfa-prep` by default):

```
~/.cfa-prep/
├── kb/                       # Knowledge files (.txt) and curriculum.json
├── mistakes/                 # Mistake log (auto-generated)
├── progress/                 # Progress file (progress.json, auto-generated)
├── flashcards/               # Flashcards (flashcards.json, manually added)
├── templates/                # IPS templates
└── config/
    └── settings.json         # Configuration (includes data_root)
```

## Knowledge File Format

`.txt` files placed in the `kb/` folder of the data root (e.g. `~/.cfa-prep/kb/`) must follow this format:

- **File name**: `l1_vol1_p1-60.txt` (level_volume_page-range)
- **Page marker**: use `===== PAGE N =====` to mark the start of each page

Example:

```
===== PAGE 1 =====
Content of page 1 here...

===== PAGE 2 =====
Content of page 2 here...
```

## Running Tests

Install pytest (once), then run it from the project root:

```bash
pip install -e .[dev]   # installs pytest as a dev dependency
pytest
```

Pytest discovers tests in `tests/` (configured via `[tool.pytest.ini_options]`
in `pyproject.toml`, including the project-root `pythonpath` so imports resolve).
This is also what the VS Code Python Test Explorer uses to discover and run the
tests. Alternatively, run the standalone script:

```bash
python -m tests.test_basic
```

## Tech Stack

- **Language**: Python 3.10+
- **Runtime dependencies**: zero external dependencies, Python standard library only
- **Dev dependencies**: pytest (for running/discovering the test suite)
- **Encoding**: UTF-8
- **Compatibility**: Windows / macOS / Linux

---

Built with CodeBuddy · CFA Prep CLI v1.0
