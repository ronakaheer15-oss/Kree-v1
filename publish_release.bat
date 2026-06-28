@echo off
setlocal
echo ========================================================
echo   KREE AI GITHUB RELEASE PUBLISHER
echo ========================================================
echo.

set "VERSION=v0.9.2.beta3"
set "RELEASE_DIR=dist\release"

:: 1. Validate Artifacts
echo [1/6] Validating artifacts...
if not exist "%RELEASE_DIR%\Kree-AI-Setup-%VERSION%.exe" (
    echo ERROR: Missing Kree-AI-Setup-%VERSION%.exe
    exit /b 1
)
if not exist "%RELEASE_DIR%\Kree-AI-%VERSION%-win64.zip" (
    echo ERROR: Missing Kree-AI-%VERSION%-win64.zip
    exit /b 1
)
if not exist "%RELEASE_DIR%\checksums.txt" (
    echo ERROR: Missing checksums.txt
    exit /b 1
)
if not exist "README-INSTALL.txt" (
    echo ERROR: Missing README-INSTALL.txt
    exit /b 1
)
if not exist "CHANGELOG.md" (
    echo ERROR: Missing CHANGELOG.md
    exit /b 1
)
echo All artifacts present.

:: 2. Verify Git Clean State
echo.
echo [2/6] Verifying Git status...
git status --porcelain > git_status.tmp
set /p GIT_STATUS=<git_status.tmp
del git_status.tmp
if not "%GIT_STATUS%"=="" (
    echo ERROR: Git repository is not clean. Commit or stash changes first.
    exit /b 1
)
echo Git is clean.

:: 3. Create Git Tag
echo.
echo [3/6] Creating git tag %VERSION%...
git tag -a %VERSION% -m "Release %VERSION%"
if errorlevel 1 (
    echo WARNING: Tag might already exist or failed.
)

:: 4. Push to Remote
echo.
echo [4/6] Pushing to remote...
git push origin main
git push origin %VERSION%
if errorlevel 1 (
    echo ERROR: Failed to push to remote.
    exit /b 1
)

:: 6. Create GitHub Release
echo.
echo [6/6] Creating GitHub Release...
gh release create %VERSION% "%RELEASE_DIR%\Kree-AI-Setup-%VERSION%.exe" "%RELEASE_DIR%\Kree-AI-%VERSION%-win64.zip" "%RELEASE_DIR%\checksums.txt" "README-INSTALL.txt" "CHANGELOG.md" -t "Kree AI %VERSION%" -F "CHANGELOG.md" --prerelease
if errorlevel 1 (
    echo ERROR: Failed to create GitHub release.
    exit /b 1
)

echo.
echo ========================================================
echo SUCCESS: Release %VERSION% published to GitHub!
echo ========================================================
pause
exit /b 0
