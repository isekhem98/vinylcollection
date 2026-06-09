@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  DuckDuckVinyl – build script (Windows)
REM  Run this from the project root directory.
REM ─────────────────────────────────────────────────────────────────────────────

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    pause & exit /b 1
)

echo [2/4] Installing build dependencies...
pip install pyinstaller requests flask >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause & exit /b 1
)

echo [3/4] Cleaning previous build artefacts...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

echo [4/4] Building EXE with PyInstaller...
python -m PyInstaller duckduckvinyl.spec

if errorlevel 1 (
    echo.
    echo *** BUILD FAILED — check the output above for errors. ***
    pause & exit /b 1
)

echo.
echo ══════════════════════════════════════════════════════════════
echo  BUILD SUCCESSFUL
echo  Your EXE is at:  dist\DuckDuckVinyl.exe
echo  Copy data.json next to the EXE on first run if you want
echo  to pre-seed your collection.
echo ══════════════════════════════════════════════════════════════
pause
