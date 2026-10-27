@echo off
title SMART CAP - MASTER AI VISION ENGINE
color 0A
echo ============================================================
echo      SMART CAP: BIHAR TALENT HUNT MASTER AI LAUNCHER
echo ============================================================
echo.
cd /d "%~dp0"

echo [1/2] Checking required AI packages...
python -m pip install ultralytics opencv-python requests --quiet

echo.
echo [2/2] Starting AI Vision Engine...
echo.
python run_ai.py

echo.
echo ============================================================
echo AI Engine Stopped.
pause
