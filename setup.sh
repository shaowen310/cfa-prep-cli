#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# CFA Prep CLI - One-click setup script
# Author: CodeBuddy AI Assistant
# Purpose: Install the package (editable, with dev extras) into the selected
#          interpreter, initialize the project, and print usage instructions.
#
# Usage:
#   ./setup.sh
#   CFA_PREP_PYTHON=/path/to/python ./setup.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  🚀 CFA Prep CLI - One-click Setup"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# 1. Resolve the interpreter we will install into
# ---------------------------------------------------------------------------
echo ""
echo "🐍 Checking Python environment..."

PYTHON=""
if [ -n "${CFA_PREP_PYTHON:-}" ]; then
    if [ -x "${CFA_PREP_PYTHON}" ]; then
        PYTHON="${CFA_PREP_PYTHON}"
    else
        echo "  ⚠️  '${CFA_PREP_PYTHON}' is not executable."
    fi
fi

if [ -z "$PYTHON" ] && [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
fi

if [ -z "$PYTHON" ] && command -v python3 &> /dev/null; then
    PYTHON=python3
elif [ -z "$PYTHON" ] && command -v python &> /dev/null; then
    PYTHON=python
fi

if [ -z "$PYTHON" ]; then
    echo "  ⚠️  Python not found, please install Python 3.10+"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo "  ✅ $PY_VERSION"
echo "  📍 Interpreter: $(command -v $PYTHON || echo $PYTHON)"

# ---------------------------------------------------------------------------
# 2. Install the package (editable) + dev extras into THAT interpreter
# ---------------------------------------------------------------------------
echo ""
echo "📦 Installing package (editable, with dev extras)..."
echo "  Target: $PYTHON"

INSTALL_OK=0

# Prefer `uv pip install --python <interpreter>`: it works even when the
# target virtualenv has no pip of its own (uv-managed / virtualenv venvs).
if command -v uv &> /dev/null; then
    echo "  → using uv"
    if uv pip install --python "$PYTHON" -e ".[dev]"; then
        INSTALL_OK=1
    fi
fi

if [ "$INSTALL_OK" -eq 0 ]; then
    echo "  → using pip"
    # Some venvs are created without pip; try to bootstrap it first.
    if ! $PYTHON -c "import pip" &> /dev/null; then
        echo "    pip missing in this interpreter, running ensurepip..."
        $PYTHON -m ensurepip --upgrade || true
    fi
    if $PYTHON -m pip install -e ".[dev]"; then
        INSTALL_OK=1
    fi
fi

if [ "$INSTALL_OK" -eq 1 ]; then
    echo "  ✅ Installed cfa-prep (editable) + pytest + pytest-cov into $PYTHON"
else
    echo "  ⚠️  Install failed. Try manually:"
    echo "      uv pip install --python \"$PYTHON\" -e \".[dev]\""
    echo "      $PYTHON -m pip install -e \".[dev]\""
    echo "      $PYTHON -m pip install pytest-cov"
fi

# Safety net: the dev extra ships pytest-cov, but environments installed
# before that was added would still miss it.
if ! $PYTHON -c "import pytest_cov" &> /dev/null; then
    echo "  → installing pytest-cov"
    if command -v uv &> /dev/null; then
        uv pip install --python "$PYTHON" pytest-cov || true
    fi
    if ! $PYTHON -c "import pytest_cov" &> /dev/null; then
        $PYTHON -m pip install pytest-cov || true
    fi
fi

# ---------------------------------------------------------------------------
# 3. Verify the install landed in THIS interpreter
# ---------------------------------------------------------------------------
echo ""
echo "🔎 Verifying environment..."
$PYTHON -c "import cfa_prep, pytest, pytest_cov; print('  ✅ cfa-prep', getattr(cfa_prep, '__version__', '1.0.0'), '| pytest', pytest.__version__, '| pytest-cov', pytest_cov.__version__)" || \
    echo "  ⚠️  Verification failed - the install may not have landed in $PYTHON"

# ---------------------------------------------------------------------------
# 4. Initialize the project
# ---------------------------------------------------------------------------
echo ""
echo "🔧 Running initialization..."
$PYTHON -m cfa_prep.main init 2>/dev/null || $PYTHON cfa_prep/main.py init 2>/dev/null || \
    echo "  ⚠️  Please run manually: cfa-prep init"

# ---------------------------------------------------------------------------
# 5. Print completion info
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  🎉 Setup complete!"
echo "============================================================"
echo ""
echo "📋 Next steps:"
echo "  1. Import your curriculum:"
echo "     cfa-prep curriculum import <file.json>"
echo "     Default data root: ~/.cfa-prep (override with CFA_PREP_HOME or cfa-prep config home <path>)"
echo ""
echo "  2. Start using:"
echo "     cfa-prep search FCFE           # Search your flashcards and mistakes"
echo "     cfa-prep quiz                  # Start quizzing"
echo "     cfa-prep recap                 # View progress"
echo "     cfa-prep flashcard --subject FRA  # Generate flashcards"
echo "     cfa-prep ips personal          # Generate IPS template"
echo ""
echo "  3. Run the tests (use the SAME interpreter you installed into):"
echo "     $PYTHON -m pytest"
echo "     $PYTHON -m pytest --cov=cfa_prep --cov-report=term-missing"
echo ""
echo "  📖 See README.md for more information"
echo ""
