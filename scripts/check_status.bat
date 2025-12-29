@echo off
REM Bot Status Checker
REM Checks if bot and MT5 are running

echo ====================================
echo   Trading Bot Status Check
echo ====================================
echo.

REM Check MT5
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] MT5 is running
) else (
    echo [X] MT5 is NOT running
)

echo.

REM Check Python bot
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Python bot is running
) else (
    echo [X] Python bot is NOT running
)

echo.
echo ====================================
echo Recent Bot Logs (Last 20 lines):
echo ====================================
echo.

REM Show recent logs if they exist
if exist "logs\bot_activity.log" (
    powershell -Command "Get-Content logs\bot_activity.log -Tail 20"
) else (
    echo No log file found
)

echo.
pause
