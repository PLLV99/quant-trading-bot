@echo off
REM Bot Status Checker
REM Checks if bot and MT5 are running

echo ====================================
echo   Trading Bot Status Check
echo ====================================
echo.

cd /d "%~dp0.."

REM Check MT5
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] MT5 is running
) else (
    echo [X] MT5 is NOT running
)

echo.

REM Check the bot specifically. Matching on IMAGENAME alone would report "OK"
REM for any unrelated Python process on the machine.
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*run_mt5_live*' };" ^
  "if ($p) { Write-Host '[OK] Trading bot is running (PID' $p.ProcessId ')' } else { Write-Host '[X] Trading bot is NOT running' }"

echo.
echo ====================================
echo Recent Bot Logs (Last 20 lines):
echo ====================================
echo.

REM Show recent logs if they exist
if exist "logs\bot_activity.log" (
    powershell -NoProfile -Command "Get-Content logs\bot_activity.log -Tail 20"
) else (
    echo No log file found
)

echo.
pause
