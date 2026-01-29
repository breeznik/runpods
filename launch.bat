@echo off
setlocal EnableDelayedExpansion
title RunPod Automation Console

:: The menu is now fully dynamic and handled by the Python script
python scripts/rpa.py interactive

if %errorlevel% neq 0 (
    echo.
    echo Script exited with error.
    pause
)
