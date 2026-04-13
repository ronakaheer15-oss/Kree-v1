@echo off
setlocal
echo ========================================================
echo   KREE AI INSTALLER BUILDER
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"

:: Check if Inno Setup is installed
where iscc >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    ) else (
        echo.
        echo ERROR: Inno Setup 6 is not installed.
        echo Download free from: https://jrsoftware.org/isinfo.php
        echo.
        echo The ZIP distribution is still available in dist\release\
        echo This step is OPTIONAL — the ZIP works fine without an installer.
        echo.
        pause
        exit /b 1
    )
) else (
    set "ISCC=iscc"
)

:: Check if PyInstaller dist exists
if not exist "%SCRIPT_DIR%..\dist\Kree AI\Kree AI.exe" (
    echo.
    echo ERROR: PyInstaller build not found.
    echo Run build_kree.bat first to create the dist folder.
    echo.
    pause
    exit /b 1
)

echo Building installer...
"%ISCC%" "%SCRIPT_DIR%kree_setup.iss"
if errorlevel 1 (
    echo.
    echo FAILED: Installer build did not complete.
    pause
    exit /b 1
)

echo.
echo SUCCESS: Installer created in dist\release\
echo.
for %%F in ("%SCRIPT_DIR%..\dist\release\Kree-AI-Setup-*.exe") do (
    echo   %%~nxF  (%%~zF bytes)
)
echo.
pause
exit /b 0
