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

REM The bot runs out of the uv-managed .venv, not a global Python. A bare
REM "python" would be missing MetaTrader5 and pandas on a fresh clone.
uv --version >NUL 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed or not in PATH
    echo Install it from https://docs.astral.sh/uv/
    pause
    exit /b 1
)

echo [OK] uv detected
echo.

REM Start the bot
REM --native-tls makes uv trust the Windows certificate store; drop it if your
REM network does not intercept TLS.
echo Starting trading bot...
echo Press Ctrl+C to stop
echo.
uv run --native-tls --extra mt5 python scripts\run_mt5_live.py

pause
