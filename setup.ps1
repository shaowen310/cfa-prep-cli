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

# 1. Check Python environment
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

    # 2. Install the package (editable) so the `cfa-prep` command is available
    Write-Host ""
    Write-Host "📦 Installing package (editable)..."
    & $PYTHON -m pip install -e . 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  pip install failed. Try: python -m pip install -e ."
    }

    # 3. Initialize the project
    Write-Host ""
    Write-Host "🔧 Running initialization..."
    & $PYTHON -m cfa_prep.main init 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Please run manually: cfa-prep init"
    }
} else {
    Write-Host "  ⚠️  Python not found, please install Python 3.10+"
}

# 4. Print completion info
Write-Host ""
Write-Host "============================================================"
Write-Host "  🎉 Setup complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "📋 Next steps:"
Write-Host "  1. Place knowledge files (.txt) into the kb/ directory of your data root"
Write-Host "     Default data root: ~/.cfa-prep (override with CFA_PREP_HOME or cfa-prep --home <path>)"
Write-Host "     File name format: l1_vol1_p1-60.txt"
Write-Host "     Mark pages inside files with ===== PAGE N ====="
Write-Host ""
Write-Host "  2. Start using:"
Write-Host "     cfa-prep search `"FCFE`"        # Search the knowledge base"
Write-Host "     cfa-prep quiz --level L1       # Start quizzing"
Write-Host "     cfa-prep recap                 # View progress"
Write-Host "     cfa-prep flashcard --subject FRA  # Generate flashcards"
Write-Host "     cfa-prep ips personal          # Generate IPS template"
Write-Host ""
Write-Host "  📖 See README.md for more information"
Write-Host ""
