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

# 1. Create directory structure
echo "📁 Creating directory structure..."
mkdir -p data/kb
mkdir -p data/mistakes
mkdir -p data/progress
mkdir -p data/flashcards
mkdir -p data/templates
mkdir -p config
mkdir -p tests
echo "  ✅ Directories created"

# 2. Generate default config file
echo ""
echo "⚙️  Generating default config..."
cat > config/settings.json << 'JSONEOF'
{
  "level": "L1",
  "version": "1.0",
  "kb_dir": "data/kb",
  "mistakes_dir": "data/mistakes",
  "progress_dir": "data/progress",
  "flashcards_dir": "data/flashcards",
  "templates_dir": "data/templates"
}
JSONEOF
echo "  ✅ config/settings.json"

# 3. Generate initial progress file
echo ""
echo "📊 Generating progress file..."
cat > data/progress/progress.md << 'MDEOF'
# CFA Study Progress

> Progress overview (updated on $(date +%Y-%m-%d))

## Mastered

(No records yet)

## Still Fuzzy

(No records yet)

## Mistake Distribution

(No data yet)

## Sole Task for Tomorrow

(No plan yet)
MDEOF
echo "  ✅ data/progress/progress.md"

# 4. Generate IPS templates
echo ""
echo "📄 Generating IPS templates..."
echo "  ✅ data/templates/ (generated via python main.py ips command)"

# 5. Check Python environment
echo ""
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

    # Initialize the project (run Python initialization)
    echo ""
    echo "🔧 Running Python initialization..."
    $PYTHON -m src.main init 2>/dev/null || $PYTHON src/main.py init 2>/dev/null || echo "  ⚠️  Please run manually: python main.py init"
fi

# 6. Print completion info
echo ""
echo "============================================================"
echo "  🎉 Setup complete!"
echo "============================================================"
echo ""
echo "📋 Next steps:"
echo "  1. Place knowledge files (.txt) into the data/kb/ directory"
echo "     File name format: l1_vol1_p1-60.txt"
echo "     Mark pages inside files with ===== PAGE N ====="
echo ""
echo "  2. Start using:"
echo "     python main.py search \"FCFE\"        # Search the knowledge base"
echo "     python main.py quiz --level L1       # Start quizzing"
echo "     python main.py recap                 # View progress"
echo "     python main.py flashcard --subject FRA  # Generate flashcards"
echo "     python main.py ips personal          # Generate IPS template"
echo ""
echo "  📖 See README.md for more information"
echo ""
