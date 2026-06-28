# Kree AI - Production Gated PyInstaller Build Pipeline
# Enforces strict read-only execution, logs per stage, and executes deep validation gates.

$ErrorActionPreference = "Stop"

# Define Paths
$KREE_ROOT = $PSScriptRoot
Set-Location -Path $KREE_ROOT

$LOG_DIR = Join-Path $KREE_ROOT "logs"
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

$LOG_BUILD   = Join-Path $LOG_DIR "build.log"
$LOG_PACKAGE = Join-Path $LOG_DIR "package.log"
$LOG_VERIFY  = Join-Path $LOG_DIR "verify.log"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KREE AI DETAILED BUILD AND VERIFICATION PIPELINE" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Helper for Phase Outlining
function Start-Phase($Name) {
    Write-Host ">>> [Phase] $Name..." -ForegroundColor Yellow
}

function End-Phase-Success($Name) {
    Write-Host "STATUS: [Phase] $Name Completed Successfully`n" -ForegroundColor Green
}

# Assert-Step Helper
function Assert-Step($Result, $ErrorMessage) {
    if (-not $Result) {
        Write-Error "CRITICAL FAILURE: $ErrorMessage"
        exit 1
    }
}

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
    
    Assert-Step ($exitCode -eq 0) "$ErrorMessage (Exit Code: $exitCode)"
}

# -- Phase 1: Environment Lock and Prep ----------------------------------------
Start-Phase "1. Environment Lock and Prep"

$venvPath = Join-Path $KREE_ROOT "venv"
Assert-Step (Test-Path $venvPath) "Virtual environment not found! Run prepare_env.ps1 first to build the environment."

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"
$venvPyInstaller = Join-Path $venvPath "Scripts\pyinstaller.exe"

Assert-Step (Test-Path $venvPython) "Virtual environment python binary not found at $venvPython!"
Assert-Step (Test-Path $venvPyInstaller) "PyInstaller not found inside venv! Ensure requirements.lock is fully restored."

# Verify no python path leakage
$activePyPath = & $venvPython -c "import sys; print(sys.executable)"
Assert-Step ($activePyPath -like "*venv*") "Global Python path leakage detected! Active Python does not point inside 'venv'."

# Python version check
$pyVersion = & $venvPython -c "import platform; print(platform.python_version())"
Write-Host "Active Virtual Env Python: $activePyPath" -ForegroundColor Gray
Write-Host "Active Python Version: $pyVersion" -ForegroundColor Gray

End-Phase-Success "1. Environment Lock and Prep"


# -- Phase 2: Workspace Clean --------------------------------------------------
Start-Phase "2. Workspace Clean"

$distPath = Join-Path $KREE_ROOT "dist"
$buildPath = Join-Path $KREE_ROOT "build"

if (Test-Path $distPath) {
    Write-Host "Clearing previous dist/ folder..." -ForegroundColor Gray
    Remove-Item -Path $distPath -Recurse -Force
}
if (Test-Path $buildPath) {
    Write-Host "Clearing previous build/ folder..." -ForegroundColor Gray
    Remove-Item -Path $buildPath -Recurse -Force
}

End-Phase-Success "2. Workspace Clean"


# -- Phase 3: Verify Environment (Read-Only) -----------------------------------
Start-Phase "3. Verify Environment"

Write-Host "Verifying dependency consistency (Read-only)..." -ForegroundColor Gray
Execute-Command -Script {
    & $venvPip check
} -ErrorMessage "Dependency graph is inconsistent! The environment is invalid."

Write-Host "Running pre-build Python runtime import validation..." -ForegroundColor Gray
Execute-Command -Script {
    & $venvPython -c "from kree.core import wakeword, runtime, auth_manager; from kree import main_entry"
} -ErrorMessage "Python runtime import validation failed! Core files crashed on import."

End-Phase-Success "3. Verify Environment"


# -- Phase 4: Executable Compilation -------------------------------------------
Start-Phase "4. Executable Compilation"

Write-Host "Running PyInstaller compilation (Output redirected to logs/build.log)..." -ForegroundColor Gray
Write-Host "This will take a few minutes. Please wait..." -ForegroundColor Gray

Execute-Command -Script {
    & $venvPyInstaller pyinstaller.spec *>$LOG_BUILD
} -ErrorMessage "PyInstaller compilation failed. Check logs/build.log"

End-Phase-Success "4. Executable Compilation"


# -- Phase 5: Release Packaging ------------------------------------------------
Start-Phase "5. Release Packaging"

Write-Host "Executing build_release.py script (Output redirected to logs/package.log)..." -ForegroundColor Gray

$releaseScript = Join-Path $KREE_ROOT "scripts\build_release.py"
Assert-Step (Test-Path $releaseScript) "Release packager script not found at $releaseScript!"

Execute-Command -Script {
    & $venvPython $releaseScript *>$LOG_PACKAGE
} -ErrorMessage "Packaging release bundle failed. Check logs/package.log"

End-Phase-Success "5. Release Packaging"


# -- Phase 6: Validation Gate (Smoke Test) -------------------------------------
Start-Phase "6. Validation Gate"

$exePath = Join-Path $KREE_ROOT "dist\Kree-v0.9.2.beta3\Kree-v0.9.2.beta3.exe"

# 1. Check File Exists
Assert-Step (Test-Path $exePath) "Executable not found at $exePath!"

# 2. Check File is non-empty
$exeSize = (Get-Item $exePath).Length
Assert-Step ($exeSize -gt 1MB) "Executable size is abnormally small ($exeSize bytes)!"

# 3. Dry-run verify version command output
Write-Host "Running smoke test dry-run with --version..." -ForegroundColor Gray
Execute-Command -Script {
    & $exePath --version *>$LOG_VERIFY
} -ErrorMessage "Smoke test failed! Version command crashed on execution. Check logs/verify.log"

# 4. Dry-run verify diagnostics command output (deep dependency verification)
Write-Host "Running smoke test dry-run with --diagnostics..." -ForegroundColor Gray
Execute-Command -Script {
    & $exePath --diagnostics *>>$LOG_VERIFY
} -ErrorMessage "Smoke test failed! System diagnostics validation crashed. Check logs/verify.log"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  PIPELINE SUCCESS" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Executable: $exePath"
Write-Host "  Size:       $exeSize bytes"
Write-Host "  Smoke Test: Passed (GUI application exited with code 0)"
Write-Host "========================================================"
Write-Host ""
