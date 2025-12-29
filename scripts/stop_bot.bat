@echo off
REM Trading Bot Stop Script
REM Gracefully stops the trading bot

echo ====================================
echo   AntiGravity Trading Bot
echo   Stopping...
echo ====================================
echo.

REM Find and kill Python processes running the bot
echo Searching for bot process...
tasklist /FI "IMAGENAME eq python.exe" /V | find "run_mt5_live" >NUL 2>&1

if "%ERRORLEVEL%"=="0" (
    echo Found running bot. Stopping...
    taskkill /F /FI "WINDOWTITLE eq run_mt5_live*" /T
    echo Bot stopped successfully.
) else (
    echo No running bot found.
)

echo.
pause
