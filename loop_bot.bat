@echo off
title AntiGravity Bot - AUTO RESTART LOOP
color 0A

:loop
echo =================================================
echo [MONITOR] Starting Bot at %time%...
echo =================================================

python scripts/run_mt5_live.py

echo.
echo [WARNING] Bot Crashed or Stopped! 
echo [MONITOR] Restarting in 5 seconds...
timeout /t 5
goto loop
