#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# CFA Prep CLI - One-click setup script
# Author: CodeBuddy AI Assistant
# Purpose: Create all necessary directories, generate a default config file, and print usage instructions.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  🚀 CFA Prep CLI - One-click Setup"
echo "============================================================"
echo ""

# 1. Check Python environment
echo "🐍 Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "  ⚠️  Python not found, please install Python 3.10+"
    PYTHON=""
fi

if [ -n "$PYTHON" ]; then
    PY_VERSION=$($PYTHON --version 2>&1)
    echo "  ✅ $PY_VERSION"

    # 2. Install the package (editable) so the `cfa-prep` command is available
    echo ""
    echo "📦 Installing package (editable)..."
    $PYTHON -m pip install -e . || echo "  ⚠️  pip install failed. Try: python -m pip install -e ."

    # 3. Initialize the project
    echo ""
    echo "🔧 Running initialization..."
    $PYTHON -m cfa_prep.main init 2>/dev/null || $PYTHON cfa_prep/main.py init 2>/dev/null || echo "  ⚠️  Please run manually: cfa-prep init"
fi

# 4. Print completion info
echo ""
echo "============================================================"
echo "  🎉 Setup complete!"
echo "============================================================"
echo ""
echo "📋 Next steps:"
echo "  1. Place knowledge files (.txt) into the kb/ directory of your data root"
echo "     Default data root: ~/.cfa-prep (override with CFA_PREP_HOME or cfa-prep --home <path>)"
echo "     File name format: l1_vol1_p1-60.txt"
echo "     Mark pages inside files with ===== PAGE N ====="
echo ""
echo "  2. Start using:"
echo "     cfa-prep search \"FCFE\"        # Search the knowledge base"
echo "     cfa-prep quiz --level L1       # Start quizzing"
echo "     cfa-prep recap                 # View progress"
echo "     cfa-prep flashcard --subject FRA  # Generate flashcards"
echo "     cfa-prep ips personal          # Generate IPS template"
echo ""
echo "  📖 See README.md for more information"
echo ""
