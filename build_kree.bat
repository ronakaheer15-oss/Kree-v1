@echo off
setlocal
echo ========================================================
echo   KREE AI BUILDER (v0.1.0 Production)
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"
set "KREE_ROOT=%SCRIPT_DIR%"

:: ── Pre-flight checks ────────────────────────────────────────────────────
echo [0/5] Pre-flight checks...

python --version >nul 2>&1
if errorlevel 1 (
    echo FAILED: Python is not installed or not in PATH.
    goto build_failed
)

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller pyinstaller-hooks-contrib --quiet
)

:: ── Clean ────────────────────────────────────────────────────────────────
echo [1/5] Cleaning previous build output...
if exist "%KREE_ROOT%dist" rmdir /s /q "%KREE_ROOT%dist"
if exist "%KREE_ROOT%build" rmdir /s /q "%KREE_ROOT%build"

:: ── Dependencies ─────────────────────────────────────────────────────────
echo [2/5] Checking dependencies...
python -m pip install -r "%KREE_ROOT%requirements.txt" --quiet
if errorlevel 1 goto build_failed

:: ── PyInstaller Build ────────────────────────────────────────────────────
echo [3/5] Starting PyInstaller Core Build...
echo       This may take 2-5 minutes. Please wait...
python -m PyInstaller --clean --noconfirm "%KREE_ROOT%Kree AI.spec" > "%KREE_ROOT%build_kree.log" 2>&1
if errorlevel 1 goto build_failed

:: ── Verify ───────────────────────────────────────────────────────────────
echo.
echo [4/5] Verifying distribution folder...
if not exist "%KREE_ROOT%dist\Kree AI\Kree AI.exe" goto build_failed

echo SUCCESS: Kree AI has been built.

:: ── CODE SIGNING (optional) ─────────────────────────────────────────────
:: ┌──────────────────────────────────────────────────────────────────────┐
:: │  TO ADD CODE SIGNING:                                                │
:: │  1. Buy a code signing certificate (Sectigo, DigiCert, Certum)      │
:: │  2. Install the certificate on this machine                          │
:: │  3. Uncomment the signtool line below and set your cert details     │
:: │                                                                      │
:: │  signtool sign /a /tr http://timestamp.digicert.com /td sha256      │
:: │    /fd sha256 "%KREE_ROOT%dist\Kree AI\Kree AI.exe"                 │
:: │                                                                      │
:: │  This removes the Windows SmartScreen "Unknown Publisher" warning.   │
:: └──────────────────────────────────────────────────────────────────────┘

:: ── Release Bundle ───────────────────────────────────────────────────────
echo [5/5] Creating release bundle...
python "%KREE_ROOT%build_release.py"
if errorlevel 1 goto build_failed

echo.
echo Release bundle created in 'dist\release'.

:: ── Size Report ──────────────────────────────────────────────────────────
echo.
echo ========================================================
echo   BUILD SIZE REPORT
echo ========================================================
echo.

:: EXE size
for %%F in ("%KREE_ROOT%dist\Kree AI\Kree AI.exe") do (
    set /a "EXE_MB=%%~zF / 1048576"
    echo   EXE size:     %%~zF bytes
)

:: Folder size
powershell -NoProfile -Command "$s=(Get-ChildItem '%KREE_ROOT%dist\Kree AI' -Recurse | Measure-Object -Property Length -Sum).Sum; $mb=[math]::Round($s/1MB,1); Write-Host \"  Dist folder:  $s bytes ($mb MB)\"; if($mb -gt 200){Write-Host '  WARNING: Build exceeds 200MB! Check for unnecessary bundled packages.' -ForegroundColor Yellow}"

:: ZIP size
for %%F in ("%KREE_ROOT%dist\release\Kree-AI-*.zip") do (
    echo   ZIP size:     %%~zF bytes
)

echo.
echo ========================================================
echo Done! Launch 'dist\Kree AI\Kree AI.exe' to test.
echo.
echo Optional: Run 'installer\build_installer.bat' to create
echo           a proper Windows installer (requires Inno Setup 6).
echo ========================================================

popd
endlocal
pause
exit /b 0

:build_failed
echo.
echo FAILED: Build did not complete correctly. Check errors above.
if exist "%KREE_ROOT%build_kree.log" (
    echo.
    echo Last build log lines:
    powershell -NoProfile -Command "Get-Content '%KREE_ROOT%build_kree.log' -Tail 40"
)
popd
endlocal
pause
exit /b 1
