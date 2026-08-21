@echo off
REM Trading Bot Stop Script
REM Gracefully stops the trading bot

echo ====================================
echo   AntiGravity Trading Bot
echo   Stopping...
echo ====================================
echo.

REM Match on the command line, not the window title. uv launches the bot as a
REM plain python.exe with no title set, so a WINDOWTITLE filter never matches
REM and a bare IMAGENAME filter would kill every Python on the machine.
echo Searching for bot process...
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*run_mt5_live*' };" ^
  "if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host 'Bot stopped successfully.' }" ^
  "else { Write-Host 'No running bot found.' }"

echo.
pause
