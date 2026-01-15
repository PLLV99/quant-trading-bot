@echo off
title AntiGravity Bot - HEALTH CHECK
echo ===================================================
echo      ANTIGRAVITY BOT - PORTFOLIO ANALYTICS
echo ===================================================
echo.
echo [SCAN] Searching for latest MT5 Report...
python scripts/analyze_history.py
echo.
echo ===================================================
echo [TIP] Save a new HTML Report from MT5 to update this data.
pause
