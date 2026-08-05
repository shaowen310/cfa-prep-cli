# -*- coding: utf-8 -*-
#
# CFA Prep CLI - One-click setup script (PowerShell / Windows)
# Author: CodeBuddy AI Assistant
# Purpose: Create all necessary directories, generate a default config file, and print usage instructions.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#   (or right-click -> Run with PowerShell after setting the execution policy)
#

$ErrorActionPreference = "Stop"

# Change to the directory where this script is located
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "============================================================"
Write-Host "  🚀 CFA Prep CLI - One-click Setup"
Write-Host "============================================================"
Write-Host ""

# 1. Create directory structure
Write-Host "📁 Creating directory structure..."
New-Item -ItemType Directory -Force -Path @(
    "data/kb",
    "data/mistakes",
    "data/progress",
    "data/flashcards",
    "data/templates",
    "config",
    "tests"
) | Out-Null
Write-Host "  ✅ Directories created"

# 2. Generate default config file
Write-Host ""
Write-Host "⚙️  Generating default config..."
$settingsJson = @'
{
  "level": "L1",
  "version": "1.0",
  "kb_dir": "data/kb",
  "mistakes_dir": "data/mistakes",
  "progress_dir": "data/progress",
  "flashcards_dir": "data/flashcards",
  "templates_dir": "data/templates"
}
'@
Set-Content -Path "config/settings.json" -Value $settingsJson -Encoding UTF8
Write-Host "  ✅ config/settings.json"

# 3. Generate initial progress file
Write-Host ""
Write-Host "📊 Generating progress file..."
$today = Get-Date -Format "yyyy-MM-dd"
$progressMd = @"
# CFA Study Progress

> Progress overview (updated on $today)

## Mastered

(No records yet)

## Still Fuzzy

(No records yet)

## Mistake Distribution

(No data yet)

## Sole Task for Tomorrow

(No plan yet)
"@
Set-Content -Path "data/progress/progress.md" -Value $progressMd -Encoding UTF8
Write-Host "  ✅ data/progress/progress.md"

# 4. Generate IPS templates
Write-Host ""
Write-Host "📄 Generating IPS templates..."
Write-Host "  ✅ data/templates/ (generated via python main.py ips command)"

# 5. Check Python environment
Write-Host ""
Write-Host "🐍 Checking Python environment..."
$PYTHON = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON = "python"
}
if (-not $PYTHON -and (Get-Command py -ErrorAction SilentlyContinue)) {
    $PYTHON = "py"
}

if ($PYTHON) {
    $PY_VERSION = & $PYTHON --version 2>&1
    Write-Host "  ✅ $PY_VERSION"

    # Initialize the project (run Python initialization)
    Write-Host ""
    Write-Host "🔧 Running Python initialization..."
    & $PYTHON -m src.main init 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Please run manually: python main.py init"
    }
} else {
    Write-Host "  ⚠️  Python not found, please install Python 3.10+"
}

# 6. Print completion info
Write-Host ""
Write-Host "============================================================"
Write-Host "  🎉 Setup complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "📋 Next steps:"
Write-Host "  1. Place knowledge files (.txt) into the data/kb/ directory"
Write-Host "     File name format: l1_vol1_p1-60.txt"
Write-Host "     Mark pages inside files with ===== PAGE N ====="
Write-Host ""
Write-Host "  2. Start using:"
Write-Host "     python main.py search `"FCFE`"        # Search the knowledge base"
Write-Host "     python main.py quiz --level L1       # Start quizzing"
Write-Host "     python main.py recap                 # View progress"
Write-Host "     python main.py flashcard --subject FRA  # Generate flashcards"
Write-Host "     python main.py ips personal          # Generate IPS template"
Write-Host ""
Write-Host "  📖 See README.md for more information"
Write-Host ""
