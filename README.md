# CFA Prep CLI

> CFA exam prep CLI tool — knowledge base search · smart quizzing · mistake analysis · progress tracking · flashcard generation · IPS templates

## Overview

CFA Prep CLI is a pure-Python command-line CFA study assistant covering all preparation needs for Levels I / II / III. It requires no third-party dependencies and works out of the box.

### Core Features

| Feature            | Description                                                        |
| ------------------ | ----------------------------------------------------------------- |
| **Knowledge Search** | Search keywords across textbook/Notes slices, with regex and fuzzy matching |
| **Smart Quiz**      | L1 mixed selection / L2 vignette / L3 scenario analysis, with mistake-priority questions |
| **Mistake Analysis** | Auto-classifies error causes (concept confusion / calculation error / misreading), generates review suggestions |
| **Progress Tracking** | Maintains a study progress file, tracks mastered and fuzzy knowledge points |
| **Flashcard Generation** | Auto-extracts Q&A from the knowledge base, supports Anki CSV export |
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
| `search <keyword>`           | Search the knowledge base    | `cfa-prep search "FCFE"`                       |
| `search --regex`             | Regex search                 | `cfa-prep search "FCF[EF]" --regex`            |
| `quiz --level L1`            | L1 quiz (10 mixed questions) | `cfa-prep quiz --level L1`                     |
| `quiz --level L2`            | L2 quiz (vignette)           | `cfa-prep quiz --level L2`                     |
| `quiz --level L3`            | L3 quiz (IPS scenario)       | `cfa-prep quiz --level L3`                     |
| `add-mistake`                | Interactive mistake entry    | `cfa-prep add-mistake`                         |
| `recap`                      | View study progress          | `cfa-prep recap`                               |
| `recap --update`             | Update study progress        | `cfa-prep recap --update`                      |
| `flashcard --subject FRA`    | Generate flashcards for a subject | `cfa-prep flashcard --subject FRA`         |
| `flashcard --anki`           | Export Anki CSV              | `cfa-prep flashcard --anki`                    |
| `ips personal`               | Generate personal IPS template | `cfa-prep ips personal`                       |
| `ips inst`                   | Generate institutional IPS template | `cfa-prep ips inst`                     |

> All commands accept the global `--home PATH` flag, e.g. `cfa-prep --home ./my-data search "FCFE"`.

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
│   ├── flashcard_generator.py   # Flashcard generation
│   ├── ips_builder.py           # IPS template building
│   └── utils.py                 # General utility functions (incl. data-root resolution)
└── tests/
    └── test_basic.py            # Basic tests
```

### Data Root Layout

Data files are stored under the configured data root (`~/.cfa-prep` by default):

```
~/.cfa-prep/
├── kb/                       # Knowledge files (.txt) — place your material here
├── mistakes/                 # Mistake log (auto-generated)
├── progress/                 # Progress files (auto-generated)
├── flashcards/               # Flashcards (auto-generated)
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

```bash
python -m tests.test_basic
```

## Tech Stack

- **Language**: Python 3.10+
- **Dependencies**: zero external dependencies, Python standard library only
- **Encoding**: UTF-8
- **Compatibility**: Windows / macOS / Linux

---

Built with CodeBuddy · CFA Prep CLI v1.0
