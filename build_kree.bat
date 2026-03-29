@echo off
echo ========================================================
echo   KREE AI BUILDER (v1.0 Production)
echo ========================================================
echo.

:: Ensure requirements are updated
echo [1/4] Checking dependencies...
python -m pip install -r requirements.txt --quiet

:: Run PyInstaller from the checked-in spec so the source tree stays consistent.
echo [2/4] Starting PyInstaller Core Build...
pyinstaller --noconfirm "Kree AI.spec"

echo.
echo [3/4] Verifying distribution folder...
if exist "dist\Kree AI" (
    echo.
    echo SUCCESS: Kree AI has been built in the 'dist' folder.
) else (
    echo.
    echo FAILED: Build did not complete correctly. Check errors above.
    pause
    exit /b
)

echo [4/4] Cleaning build artifacts...
:: del /f /q "Kree AI.spec"
:: rmdir /s /q "build"

echo.
echo Done! Launch 'dist\Kree AI\Kree AI.exe' to test.
pause
