# Kree AI - Strict Environment Provisioning Pipeline
# Creates the virtual environment, restores locked dependencies, and validates environment integrity.

$ErrorActionPreference = "Stop"

# Define Paths
$KREE_ROOT = $PSScriptRoot
Set-Location -Path $KREE_ROOT

$LOG_DIR = Join-Path $KREE_ROOT "logs"
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

$LOG_PREP = Join-Path $LOG_DIR "prep.log"
$LOCK_FILE = Join-Path $KREE_ROOT "requirements.lock"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KREE AI ENVIRONMENT PROVISIONER" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Helper to run native tools safely under strict ErrorActionPreference
function Execute-Command {
    param(
        [Parameter(Mandatory=$true)]
        [scriptblock]$Script,
        [string]$ErrorMessage
    )
    
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    
    Invoke-Command -ScriptBlock $Script
    $exitCode = $LASTEXITCODE
    
    $ErrorActionPreference = $oldEAP
    
    if ($exitCode -ne 0) {
        Write-Error "CRITICAL FAILURE: $ErrorMessage (Exit Code: $exitCode)"
        exit 1
    }
}

# 1. Create/Verify Virtual Environment
Write-Host ">>> Phase 1: Creating virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $KREE_ROOT "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating fresh virtual environment..." -ForegroundColor Gray
    Execute-Command -Script { & python -m venv venv } -ErrorMessage "Failed to create python virtual environment."
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment python binary not found at $venvPython!"
    exit 1
}

# Verify no python path leakage
$activePyPath = & $venvPython -c "import sys; print(sys.executable)"
if ($activePyPath -notlike "*venv*") {
    Write-Error "CRITICAL: Global Python path leakage detected! Active Python does not point inside 'venv'."
    exit 1
}

# 2. Restore Dependencies from Lockfile
Write-Host ">>> Phase 2: Restoring locked dependencies (Output redirected to logs/prep.log)..." -ForegroundColor Yellow
if (-not (Test-Path $LOCK_FILE)) {
    Write-Error "CRITICAL: Lockfile not found at $LOCK_FILE! Cannot perform deterministic restore."
    exit 1
}

# Ensure pip is up to date first
Execute-Command -Script {
    & $venvPython -m pip install --upgrade pip --quiet *>$LOG_PREP
} -ErrorMessage "Failed to upgrade pip inside venv. Check logs/prep.log"

# Install requirements from lockfile
Execute-Command -Script {
    & $venvPip install -r $LOCK_FILE --quiet *>>$LOG_PREP
} -ErrorMessage "Failed to install locked requirements. Check logs/prep.log"

# 3. Environment Consistency Check
Write-Host ">>> Phase 3: Running dependency consistency check..." -ForegroundColor Yellow
Execute-Command -Script {
    & $venvPip check *>>$LOG_PREP
} -ErrorMessage "Pip consistency check failed. Broken dependencies found! Check logs/prep.log"

# 4. Pre-Build Runtime Import Validation
Write-Host ">>> Phase 4: Running pre-build Python import validation..." -ForegroundColor Yellow
Execute-Command -Script {
    & $venvPython -c "from kree.core import wakeword, runtime, auth_manager; from kree import main_entry" *>>$LOG_PREP
} -ErrorMessage "Python runtime import validation failed! One of the core modules crashed on import. Check logs/prep.log"

# Save install snapshot
$snapshotPath = Join-Path $LOG_DIR "install_snapshot.txt"
Get-Content $LOCK_FILE | Out-File -FilePath $snapshotPath -Encoding utf8 -Force

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  ENVIRONMENT PROVISION SUCCESS" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Virtual Env:  $venvPath"
Write-Host "  Dependencies: Fully restored from requirements.lock"
Write-Host "  Integrity:    Valid (pip check passed)"
Write-Host "  Imports:      Valid (core modules imported without crashing)"
Write-Host "========================================================"
Write-Host ""
