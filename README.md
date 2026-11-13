# CFA Prep CLI

> CFA exam prep CLI tool — smart quizzing · mistake analysis · progress tracking · flashcards · IPS templates

## Overview

CFA Prep CLI is a pure-Python command-line CFA study assistant covering all preparation needs for Levels I / II / III. It requires no third-party dependencies and works out of the box.

### Core Features

| Feature            | Description                                                        |
| ------------------ | ----------------------------------------------------------------- |
| **Search** | Search your curriculum, your flashcards and your mistake log, with regex and fuzzy matching |
| **Smart Quiz**      | L1 module review / L2 vignette / L3 scenario analysis, with mistake-priority questions |
| **Mistake Analysis** | Logs mistakes (MCQ or free-form), tracks subjects and modules, generates review suggestions |
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
| **`CFA_PREP_HOME` env var** | `export CFA_PREP_HOME=/path/to/data` |
| **`config home <path>`** | `cfa-prep config home D:\cfa\data` (persisted in `<data_root>/config/home.env`) |

The data of each command lives in its own subfolder of the data root — see
[Data Root Layout](#data-root-layout).

### 4. Import your curriculum

```bash
cfa-prep curriculum import my-curriculum.json
```

### 5. Start using

```bash
cfa-prep search FCFE
```

## Command Reference

| Command                      | Description                  | Example                                        |
| ---------------------------- | ---------------------------- | ---------------------------------------------- |
| `init`                       | Initialize data root dirs and config | `cfa-prep init`                          |
| `config level`               | Show the current default level | `cfa-prep config level`                  |
| `config level L2`            | Set the default level (L1/L2/L3) | `cfa-prep config level L2`               |
| `config home`                | Show the data root directory path | `cfa-prep config home`                  |
| `config home <path>`         | Set the data root to an existing folder | `cfa-prep config home D:\cfa\data` |
| `search <keyword>`           | Search your curriculum, flashcards and mistakes | `cfa-prep search FCFE`      |
| `search --regex`             | Regex search                 | `cfa-prep search "FCF[EF]" --regex`            |
| `search --no-fuzzy`          | Exact matching only (higher precision) | `cfa-prep search FCFE --no-fuzzy`   |
| `quiz`                       | Quiz at the configured level (set via `config level`) | `cfa-prep quiz`                          |
| `quiz --no-randomize`        | Disable question/option shuffling | `cfa-prep quiz --no-randomize`             |
| `stats`                      | Quiz statistics and review schedule | `cfa-prep stats`                        |
| `stats --reset`              | Clear all stored quiz statistics | `cfa-prep stats --reset`                    |
| `mistake`                    | Recent mistakes and the log by subject and module | `cfa-prep mistake`                    |
| `mistake -a`                 | Interactive mistake entry    | `cfa-prep mistake -a`                          |
| `recap`                      | View study progress          | `cfa-prep recap`                               |
| `recap --update`             | Update study progress        | `cfa-prep recap --update`                      |
| `recap --remove`             | Remove progress entries      | `cfa-prep recap --remove`                      |
| `flashcard -a`               | Manually add a flashcard (select subject/module from the curriculum) | `cfa-prep flashcard -a` |
| `flashcard -a`               | Shorthand for `--add`        | `cfa-prep flashcard -a`                       |
| `flashcard --review`         | Review cards (reveal answer or skip) | `cfa-prep flashcard --review`           |
| `flashcard -r`               | Shorthand for `--review`     | `cfa-prep flashcard -r`                       |
| `ips personal`               | Generate personal IPS template | `cfa-prep ips personal`                       |
| `ips inst`                   | Generate institutional IPS template | `cfa-prep ips inst`                     |
| `baii`                       | Interactive BA II Plus financial calculator | `cfa-prep baii`                 |
| `curriculum seed`            | Create an empty curriculum    | `cfa-prep curriculum seed`                   |
| `curriculum import <file>`   | Replace curriculum from a JSON file | `cfa-prep curriculum import my.json`   |
| `curriculum show`            | Display the current curriculum | `cfa-prep curriculum show`                   |

> The data root can be set persistently with `cfa-prep config home ./my-data` or via the `CFA_PREP_HOME` environment variable, e.g. `export CFA_PREP_HOME=./my-data`.

## Search

`cfa-prep search <keyword>` looks the keyword up in **every source you have written**, so
one command covers your curriculum, your flashcards and the questions you got wrong:

| Source | Where it lives | What is searched |
| --- | --- | --- |
| 📘 Curriculum | `<data_root>/curriculum/curriculum.json` | module names and topic titles |
| 🗂️ Flashcards | `<data_root>/flashcards/flashcards.json` | question and answer |
| ❌ Mistake log | `<data_root>/mistakes/mistakes.json` | question, options and explanation |

Every hit shows where it came from:

```
============================================================
  🔍 Search: tariff
============================================================

Curriculum: 93 modules / 583 topics | Flashcards: 5 | Mistakes: 66

Found 3 result(s):

────────────────────────────────────────────────────────────
  📘 [1] Module 4: Monetary Policy — Economics > Module 4: Monetary Policy (L1)

────────────────────────────────────────────────────────────
  ❌ [1] Which of the following trade restrictions is likely to result in the
      greatest welfare loss for the importing country? — Economics > Module 6:
      International Trade
────────────────────────────────────────────────────────────
  ...s is likely to result in the greatest welfare loss for the importing country?
  A tariff
```

The matches are **whole words**: `tariff` finds "a tariff" but not "tariffs" (use
`--regex "tariffs?"` to catch both). A phrase can be typed **without quotes** —
`cfa-prep search free cash flow` is the same as `cfa-prep search "free cash flow"`.
Fuzzy matching (an approximate spelling or an abbreviation) is applied per word as a
fallback; use `--no-fuzzy` for exact matching only, and `--regex` for a regular
expression. `--max-results` caps the hits **per source**, so one source can never hide
the others.

In the curriculum the **module is the unit**: a module whose name matches is one hit
on its own, otherwise every matching topic of that module is a hit. A curriculum hit
shows no detail block — the title already is the content.

## Curriculum

The **curriculum** is the single source of truth for the subjects and topics you study
(per level L1/L2/L3). It drives quiz topic selection and (in a later pass) input
auto-correction and progress-coverage percentages.

There is **no bundled default scaffold** — the curriculum starts empty and is populated
by you via `cfa-prep curriculum import`. `cfa-prep init` only creates an empty
`curriculum/curriculum.json`. Because actual CFA curriculum text is copyrighted by CFA
Institute, you should provide your own legally-owned material (your notes, or a topic
list you export yourself).

The curriculum is stored at `<data_root>/curriculum/curriculum.json` with this shape — each
subject maps to one or more **modules**, and each module maps to a list of topics:

```json
{
  "L1": {
    "Financial Statement Analysis": {
      "Module 1: Analysis Framework": [
        "1.01 Introduction to financial statement analysis",
        "1.02 Financial reporting standards"
      ],
      "Module 2: The Financial Statements": [
        "2.01 Understanding the income statement",
        "2.02 Understanding the balance sheet"
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

## Quiz Statistics & Smart Review

The statistics hold **questions only** — the mistakes you logged and answered again.
Each of them keeps its own schedule in `<data_root>/progress/quiz_stats.json`, and the
next quiz is built from those statistics so that weak and forgotten material comes back
first — while things you already know are asked less often.

A curriculum topic has no record of its own: the CLI shows you the topics of a module
and you answer them from your own book, so the tool never sees the question. What it
knows about a topic is what the mistake log tells it — which **module** the mistakes
belong to. The module is therefore the unit the quiz reviews.

The data is split across two files, because the two halves have different jobs:

| File | Holds | Used for |
| --- | --- | --- |
| `progress/quiz_stats.json` | Per-question scheduling state | Choosing which questions to ask |
| `progress/quiz_sessions.json` | Session history (capped at 200) | Reporting overall accuracy |

The per-question file is the one on the hot path — it is read and written once per quiz,
not once per answer.

### Question identity

A logged mistake is stored under a short hash of the question's identity instead of its
full text:

| Entry | Key | Example |
| --- | --- | --- |
| Logged mistake | `q:` + hash(question text + options) | `q:9d5498fe9b6bfe5f` |

The options are part of the identity because two different questions can share the same
stem, but the **correct answer is not** — re-logging a question with a fixed answer keeps
its history attached. The hash ignores cosmetic whitespace and case and does not depend
on the order the options are displayed in, so a question that was logged twice still
counts as one question.

The id is created **once**, when the mistake is logged, and stored with the record in
`mistakes.json`:

```json
{
  "date": "20261108",
  "subject": "Financial Statement Analysis",
  "module": "Module 3: Financial Statements",
  "question": "An independent audit report is most likely to provide:",
  "question_id": "q:9d5498fe9b6bfe5f",
  "options": ["absolute assurance ...", "a qualified opinion ...", "reasonable assurance ..."],
  "..."
}
```

`mistakes.json` is the single source of truth for the id: the quiz engine reads it from
there instead of deriving it again, and a mistake that is re-logged after a wrong answer
carries the id of the original question. The statistics file only refers to that id.

The topic is **not** stored with the entry. A question belongs to a topic, but that link
lives where the truth is: the curriculum owns the curriculum topics, and the mistake
log owns the logged mistakes. The quiz engine joins the two when it selects what to
ask, so the statistics file stays a pure store of questions.

### Mistake attribution: subject + module

A mistake is attributed to its **subject and module**, both taken from the curriculum.
No topic is recorded — a topic typed by the user can be wrong, while the subject/module
pair is always a curriculum value. The module is therefore **required**: a mistake
without one cannot be attributed and is rejected.

| Value | Trust | Recorded with the mistake |
| --- | --- | --- |
| Subject | Curriculum value | ✅ |
| Module | Curriculum value | ✅ (required) |
| Topic | Typed by the user | ❌ not recorded |

The **module is the unit the quiz reviews**. A mistake belongs to a module, the module
carries the score, and the quiz asks you about the modules you are weak in:

- the **questions** are the logged mistakes, at most **2 per module**, so a single weak
  module cannot take over the session. Ten questions under that cap therefore cover at
  least **5 modules**; modules with a thin history push the count up.
- the **material** is the topic list of the modules those questions came from, plus one
  module without mistakes so that new material keeps coming back.

Nothing is tracked per topic: the topic list of a module is material to work through,
not a queue of items, so the whole list is shown every time.

### Where the mistake log is summarized

A logging session (`cfa-prep mistake -a`) covers a single subject and module and ends
with one line that says what was added:

```
✅ Session complete — 1 mistake saved for Economics > Module 6: International Trade.
```

The **full summary** of the whole log — every subject and module — belongs to
`cfa-prep mistake` (alias `cfa-prep mis`). The order is the **curriculum order**: the
subjects as they appear in the exam, and inside a subject the modules in their
curriculum order:

```
--- Mistake log by subject and module (41 mistakes) ---
  8 — Economics > Module 2: Understanding Business Cycles
  5 — Economics > Module 3: Fiscal Policy
  5 — Economics > Module 6: International Trade
  5 — Corporate Issuers > Module 1: Organizational Forms, Corporate Issuer Features, and Ownership
  7 — Financial Statement Analysis > Module 1: Introduction to Financial Statement Analysis
  ...
```

### How it works

Every logged mistake keeps its own schedule (a spaced-repetition style model):

| Outcome | Effect |
| --- | --- |
| ✅ Correct | It rests for longer (1 → 3 → 7 → 14 days, then `interval × ease`), and its **ease** grows, so it is selected less often. |
| ❌ Wrong | It is due **immediately** (0 days) and its ease drops, so it is selected more often. |
| ⏭️ Skipped | It was never really tested — it stays due now and keeps some priority. |

Questions are then scored by **priority**:

```
priority = overdue(≤ +3.0) + 4.0·wrong_ratio + 0.8·min(wrong, 5)
           + 1.5·min(skipped, 2) − 2.0·min(streak/3, 1)
```

A module is as urgent as the most urgent mistake logged in it, and a module without any
mistake counts as unseen. That way one badly known question lifts the whole module,
while a module whose mistakes are all mastered is pushed back. The questions of a quiz
are the most urgent ones — the ones that are due or that you keep getting wrong come
first.

The due date is **not stored** in `quiz_stats.json` — it is always derived as
`last_seen + interval_days`, so there is a single source of truth and the two can
never drift apart. Only `interval_days` is persisted, because for a long streak it
depends on the previous interval and cannot be recomputed from the current streak
alone.

### Answering

The quiz replays your logged mistakes as real multiple-choice questions and scores them
automatically — the correct answer is part of the mistake record. At most **2 questions
per module** are replayed, so the review spreads over your weak modules instead of
repeating the same one.

The curriculum topics are material, not questions: the CLI shows the topics of the
modules under review and you work through them from your book, so there is nothing to
grade and nothing to record. If you get one wrong, log it with `cfa-prep mistake -a` —
the module it belongs to then comes back first in the next quiz.

### Viewing the statistics

```bash
cfa-prep stats           # accuracy, weakest subjects, questions to review, due list
cfa-prep stats --reset   # clear all stored statistics
```

## Flashcards

Flashcards are created **manually** — there is no automatic Q&A extraction. Run the
interactive add flow, pick the **subject** and **module** from the curriculum, then
enter the front (question) and back (answer):

```bash
cfa-prep flashcard -a    # or: cfa-prep flashcard -a
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

## BA II Plus Calculator

Launch an interactive emulator of the Texas Instruments **BA II Plus** financial
calculator used in the CFA exams:

```bash
cfa-prep baii
```

Type a command and optionally a value; use `HELP` for the command list and
`QUIT` to exit. Commands are kept short (no `/`) for fast entry:

| Command              | Description                                        |
| -------------------- | -------------------------------------------------- |
| `N` `IY` `PV` `PMT` `FV` `<v>` | Set a TVM register                     |
| `CPT <N\|IY\|PV\|PMT\|FV>`   | Solve a TVM register                  |
| `CF <amount> [freq]` | Add a cash flow (`CF0` is the first entry)          |
| `NPV <rate%>`        | Net present value at an annual rate                 |
| `IRR`                | Internal rate of return (annual %)                  |
| `STAT <x...>`        | One-variable statistics (mean, sample SD `Sx`)      |
| `STAT2 <x y...>`     | Two-variable statistics (slope, intercept, corr)    |
| `CHG <old> <new>`    | Percent change                                      |
| `RESET`              | Clear all registers                                 |
| `HELP` / `QUIT`      | Help / exit                                         |

You can also type a raw arithmetic expression for quick calculations
(`+ - * / // % **`, parentheses, and `^` for exponentiation are supported):

```
baii> 1+2             → = 3
baii> 2^10            → = 1,024
baii> 3*(4-1)^2       → = 27
baii> 100/3           → = 33.3333
```

Example session:

```
baii> PV 1000
baii> IY 5
baii> N 10
baii> PMT 0
baii> CPT FV          → FV = -1628.8946   (BA II Plus sign convention)
```

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
│   ├── search.py                # Unified search (flashcards + mistake log)
│   ├── quiz_engine.py           # Quiz engine
│   ├── quiz_stats.py            # Quiz statistics, spaced-repetition scheduling, smart selection
│   ├── mistake_analyzer.py      # Mistake analyzer
│   ├── progress_tracker.py      # Progress tracking
│   ├── flashcard_generator.py   # Manual flashcard management
│   ├── ips_builder.py           # IPS template building
│   ├── curriculum.py            # Curriculum module (subjects + topics per level)
│   ├── baii_calculator.py       # BA II Plus financial calculator emulator
│   └── utils.py                 # General utility functions (incl. data-root resolution)
└── tests/
    └── test_basic.py            # Basic tests
```

### Data Root Layout

Data files are stored under the configured data root (`~/.cfa-prep` by default).
Every folder belongs to one command:

| Folder | Command | Content |
| --- | --- | --- |
| `flashcards/` | `cfa-prep flashcard` | `flashcards.json` (manually added) |
| `mistakes/` | `cfa-prep mistake` | `mistakes.json` (auto-generated) |
| `curriculum/` | `cfa-prep curriculum` | `curriculum.json` (subjects, modules, topics) |
| `progress/` | `cfa-prep recap` / `cfa-prep stats` | `progress.json`, `quiz_stats.json`, `quiz_sessions.json` |
| `templates/` | `cfa-prep ips` | IPS templates |
| `config/` | `cfa-prep config` | `settings.json`, `home.env` |

```
~/.cfa-prep/
├── mistakes/                 # Mistake log (auto-generated)
├── progress/                 # Progress files (progress.json, quiz_stats.json, quiz_sessions.json — auto-generated)
├── flashcards/               # Flashcards (flashcards.json, manually added)
├── curriculum/               # Curriculum (curriculum.json)
├── templates/                # IPS templates
└── config/
    ├── settings.json         # Configuration (level, directory names)
    └── home.env              # Persisted data root (written by `config home <path>`)
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
