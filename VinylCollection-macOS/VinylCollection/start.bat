@echo off
REM Vinyl Collection Dashboard — Windows Launcher

echo ============================================
echo Vinyl Collection Dashboard
echo ============================================

REM Check for SSL certificates
if not exist "cert.pem" (
    echo [WARNING] SSL certificates not found.
    echo          Run .\setup_ssl.ps1 to generate trusted certificates and eliminate browser warnings.
    echo.
)

REM Try to find Python and install dependencies
setlocal enabledelayedexpansion

REM First try 'py' launcher (modern Windows Python)
py -c "import sys; print('Found py launcher')" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python detected with 'py' command
    echo Installing dependencies...
    py -m pip install -q -r requirements.txt 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Dependencies installed
        echo.
        echo Starting Vinyl Collection...
        echo Access at: https://127.0.0.1:5000
        echo (Note: Accept SSL certificate warning or run .\setup_ssl.ps1 for trusted certificates)
        echo.
        py run.py
    ) else (
        echo [ERROR] Failed to install dependencies
        echo Try running in PowerShell instead: .\start.ps1
        pause
    )
) else (
    echo [WARNING] 'py' launcher not found, trying 'python' command...
    python -c "import sys; print('Found python')" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Python detected with 'python' command
        echo Installing dependencies...
        python -m pip install -q -r requirements.txt 2>nul
        if %errorlevel% equ 0 (
            echo [OK] Dependencies installed
            echo.
            echo Starting Vinyl Collection...
            echo Access at: https://127.0.0.1:5000
            echo (Note: Accept SSL certificate warning or run .\setup_ssl.ps1 for trusted certificates)
            echo.
            python run.py
        ) else (
            echo [ERROR] Failed to install dependencies
            echo Try running in PowerShell instead: .\start.ps1
            pause
        )
    ) else (
        echo [ERROR] Python not found in PATH
        echo.
        echo Solutions:
        echo   1. Use PowerShell: .\start.ps1
        echo   2. Ensure Python is installed: https://www.python.org/downloads/
        echo   3. Add Python to PATH in Windows settings
        echo.
        pause
    )
)