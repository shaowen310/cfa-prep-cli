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

Run the one-click setup script for your platform (creates all directories, config, and progress file):

```bash
# Linux/macOS
./setup.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Or initialize manually:

```bash
# 1. Initialize the project
python main.py init

# 2. Place knowledge files into the data/kb/ directory
#    File name format: l1_vol1_p1-60.txt
#    Mark pages inside files with ===== PAGE N =====

# 3. Start using
python main.py search "FCFE"
```

## Command Reference

| Command                      | Description                  | Example                                        |
| ---------------------------- | ---------------------------- | ---------------------------------------------- |
| `init`                       | Initialize project directories and config | `python main.py init`                  |
| `search <keyword>`           | Search the knowledge base    | `python main.py search "FCFE"`                 |
| `search --regex`             | Regex search                 | `python main.py search "FCF[EF]" --regex`      |
| `quiz --level L1`            | L1 quiz (10 mixed questions) | `python main.py quiz --level L1`               |
| `quiz --level L2`            | L2 quiz (vignette)           | `python main.py quiz --level L2`               |
| `quiz --level L3`            | L3 quiz (IPS scenario)       | `python main.py quiz --level L3`               |
| `add-mistake`                | Interactive mistake entry    | `python main.py add-mistake`                   |
| `recap`                      | View study progress          | `python main.py recap`                         |
| `recap --update`             | Update study progress        | `python main.py recap --update`                |
| `flashcard --subject FRA`    | Generate flashcards for a subject | `python main.py flashcard --subject FRA`   |
| `flashcard --anki`           | Export Anki CSV              | `python main.py flashcard --anki`              |
| `ips personal`               | Generate personal IPS template | `python main.py ips personal`                 |
| `ips inst`                   | Generate institutional IPS template | `python main.py ips inst`               |

## Directory Structure

```
cfa-prep-cli/
├── README.md                    # This file
├── setup.sh                     # One-click setup script (Linux/macOS)
├── setup.ps1                    # One-click setup script (Windows/PowerShell)
├── .gitignore
├── src/
│   ├── main.py                  # CLI entry point
│   ├── knowledge_base.py        # Knowledge base management
│   ├── quiz_engine.py           # Quiz engine
│   ├── mistake_analyzer.py      # Mistake analyzer
│   ├── progress_tracker.py      # Progress tracking
│   ├── flashcard_generator.py   # Flashcard generation
│   ├── ips_builder.py           # IPS template building
│   └── utils.py                 # General utility functions
├── data/
│   ├── kb/                      # Knowledge files (.txt)
│   ├── mistakes/                # Mistake log (auto-generated)
│   ├── progress/                # Progress files (auto-generated)
│   ├── flashcards/              # Flashcards (auto-generated)
│   └── templates/               # IPS templates
├── config/
│   └── settings.json            # Configuration file
└── tests/
    └── test_basic.py            # Basic tests
```

## Knowledge File Format

`.txt` files placed in `data/kb/` must follow this format:

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
