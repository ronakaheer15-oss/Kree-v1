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
    ) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
        set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
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
if not exist "%SCRIPT_DIR%..\dist\Kree-v0.9.2.beta3\Kree-v0.9.2.beta3.exe" (
    echo.
    echo ERROR: PyInstaller build not found.
    echo Run build_kree.bat first to create the dist folder.
    echo.
    pause
    exit /b 1
)

:: Validate Critical Dependencies
echo Validating PyInstaller bundle...
if not exist "%SCRIPT_DIR%..\dist\Kree-v0.9.2.beta3\_internal\assets\models\" (
    echo ERROR: Missing assets\models folder in bundle!
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%..\dist\Kree-v0.9.2.beta3\_internal\stitch_core_system_dashboard\" (
    echo ERROR: Missing stitch_core_system_dashboard folder in bundle!
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%..\dist\Kree-v0.9.2.beta3\_internal\openwakeword\" (
    echo ERROR: Missing openwakeword folder in bundle!
    pause
    exit /b 1
)
echo Validation passed.

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

echo Generating SHA256 checksums...
pushd "%SCRIPT_DIR%..\dist\release"
if exist checksums.txt del checksums.txt
for %%F in (*.exe *.zip) do (
    certutil -hashfile "%%F" SHA256 | findstr /v "hash" >> checksums.txt
    echo %%F >> checksums.txt
    echo. >> checksums.txt
)
popd
echo Checksums generated in dist\release\checksums.txt
echo.

pause
exit /b 0
