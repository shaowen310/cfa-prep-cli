# -*- coding: utf-8 -*-
#
# CFA Prep CLI - One-click setup script (PowerShell / Windows)
# Author: CodeBuddy AI Assistant
# Purpose: Create all necessary directories, install the package (editable, with dev extras),
#          generate a default config file, and print usage instructions.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#   powershell -ExecutionPolicy Bypass -File setup.ps1 -Python C:\Users\me\.venvs\cfa-prep-cli\Scripts\python.exe
#   (or right-click -> Run with PowerShell after setting the execution policy)
#

param(
    # Optional: explicit interpreter to install into. Defaults to the active virtualenv,
    # then whatever `python` / `py` is on PATH.
    [string]$Python = "",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

# Change to the directory where this script is located
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "============================================================"
Write-Host "  🚀 CFA Prep CLI - One-click Setup"
Write-Host "============================================================"
Write-Host ""

function Get-NativeOutput {
    param([scriptblock]$Command)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        return (& $Command 2>&1 | Out-String).Trim()
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Write-Step($message) {
    Write-Host ""
    Write-Host $message
}

# Run a native command, merging stderr into stdout and printing plain text.
# Native stderr would otherwise become a terminating error under
# $ErrorActionPreference = "Stop" on Windows PowerShell 5.1.
function Invoke-Native {
    param([scriptblock]$Command)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command 2>&1 | ForEach-Object { Write-Host ("    {0}" -f $_.ToString()) }
    } finally {
        $ErrorActionPreference = $prev
    }
}

# ---------------------------------------------------------------------------
# 1. Resolve the interpreter we will install into
# ---------------------------------------------------------------------------
Write-Step "🐍 Checking Python environment..."

$PYTHON_EXE = $null

if ($Python) {
    if (Test-Path $Python) {
        $PYTHON_EXE = (Resolve-Path $Python).Path
    } else {
        Write-Host "  ⚠️  '$Python' does not exist."
    }
}

if (-not $PYTHON_EXE -and $env:VIRTUAL_ENV) {
    $candidate = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
    if (Test-Path $candidate) { $PYTHON_EXE = $candidate }
}

if (-not $PYTHON_EXE -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $PYTHON_EXE = (Get-Command python).Source
}

if (-not $PYTHON_EXE -and (Get-Command py -ErrorAction SilentlyContinue)) {
    $PYTHON_EXE = (Get-Command py).Source
}

if (-not $PYTHON_EXE) {
    Write-Host "  ⚠️  Python not found, please install Python 3.10+"
    exit 1
}

$PY_VERSION = Get-NativeOutput { & $PYTHON_EXE --version }
Write-Host "  ✅ $PY_VERSION"
Write-Host "  📍 Interpreter: $PYTHON_EXE"

# ---------------------------------------------------------------------------
# 2. Install the package (editable) + dev extras into THAT interpreter
# ---------------------------------------------------------------------------
if (-not $SkipInstall) {
    Write-Step "📦 Installing package (editable, with dev extras)..."
    Write-Host "  Target: $PYTHON_EXE"

    $installOk = $false

    # Prefer `uv pip install --python <interpreter>`: it works even when the
    # target virtualenv has no pip of its own (uv-managed / virtualenv venvs).
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "  → using uv"
        Invoke-Native { & uv pip install --python $PYTHON_EXE -e ".[dev]" }
        if ($LASTEXITCODE -eq 0) { $installOk = $true }
    }

    if (-not $installOk) {
        Write-Host "  → using pip"
        # Some venvs are created without pip; try to bootstrap it first.
        & $PYTHON_EXE -c "import pip" *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    pip missing in this interpreter, running ensurepip..."
            Invoke-Native { & $PYTHON_EXE -m ensurepip --upgrade }
        }
        Invoke-Native { & $PYTHON_EXE -m pip install -e ".[dev]" }
        if ($LASTEXITCODE -eq 0) { $installOk = $true }
    }

    if ($installOk) {
        Write-Host "  ✅ Installed cfa-prep (editable) + pytest into $PYTHON_EXE"
    } else {
        Write-Host "  ⚠️  Install failed. Try manually:"
        Write-Host ('      uv pip install --python "{0}" -e ".[dev]"' -f $PYTHON_EXE)
        Write-Host "      # or"
        Write-Host ('      "{0}" -m pip install -e ".[dev]"' -f $PYTHON_EXE)
    }
} else {
    Write-Step "⏭️  Skipping install (-SkipInstall)."
}

# ---------------------------------------------------------------------------
# 3. Verify the install landed in THIS interpreter
# ---------------------------------------------------------------------------
Write-Step "🔎 Verifying environment..."
$verify = "import cfa_prep, pytest; print('  [OK] cfa-prep', getattr(cfa_prep, '__version__', '1.0.0'), '| pytest', pytest.__version__)"
Invoke-Native { & $PYTHON_EXE -c $verify }

# ---------------------------------------------------------------------------
# 4. Initialize the project
# ---------------------------------------------------------------------------
Write-Step "🔧 Running initialization..."
Invoke-Native { & $PYTHON_EXE -m cfa_prep.main init }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠️  Please run manually: cfa-prep init"
}

# ---------------------------------------------------------------------------
# 5. Print completion info
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================"
Write-Host "  🎉 Setup complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "📋 Next steps:"
Write-Host "  1. Import your curriculum:"
Write-Host "     cfa-prep curriculum import <file.json>"
Write-Host "     Default data root: ~/.cfa-prep (override with CFA_PREP_HOME or cfa-prep config home <path>)"
Write-Host ""
Write-Host "  2. Start using:"
Write-Host "     cfa-prep search FCFE           # Search your flashcards and mistakes"
Write-Host "     cfa-prep quiz                  # Start quizzing"
Write-Host "     cfa-prep recap                 # View progress"
Write-Host "     cfa-prep flashcard --subject FRA  # Generate flashcards"
Write-Host "     cfa-prep ips personal          # Generate IPS template"
Write-Host ""
Write-Host "  3. Run the tests (use the SAME interpreter you installed into):"
Write-Host ('     & "{0}" -m pytest' -f $PYTHON_EXE)
Write-Host ""
Write-Host "  📖 See README.md for more information"
Write-Host ""
