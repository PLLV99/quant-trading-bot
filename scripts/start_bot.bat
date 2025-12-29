@echo off
REM Trading Bot Startup Script for Windows
REM Run this to start the bot

echo ====================================
echo   AntiGravity Trading Bot
echo   Starting...
echo ====================================
echo.

REM Navigate to bot directory
cd /d "%~dp0.."

REM Check if MT5 is running
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo [WARNING] MetaTrader 5 is not running!
    echo Please start MT5 first and login to your Exness account.
    echo.
    pause
    exit /b 1
)

echo [OK] MT5 is running
echo.

REM Check Python installation
python --version >NUL 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [OK] Python detected
echo.

REM Start the bot
echo Starting trading bot...
echo Press Ctrl+C to stop
echo.
python scripts\run_mt5_live.py

pause
