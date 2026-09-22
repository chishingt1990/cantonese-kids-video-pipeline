@echo off
title Gemini CLI - Autonomous Coding Agent
cd /d "%~dp0"
set PATH=%APPDATA%\npm;C:\Program Files\nodejs;C:\Program Files\Git\cmd;%PATH%

echo ============================================================
echo   Starting Gemini CLI Agent for Cantonese Kids Studio
echo ============================================================
echo.
call gemini
echo.
echo ============================================================
echo   Gemini CLI session ended. Press any key to close this window.
echo ============================================================
pause
