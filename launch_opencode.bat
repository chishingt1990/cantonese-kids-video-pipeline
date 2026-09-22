@echo off
title OpenCode AI - Terminal Coding Agent
cd /d "%~dp0"
set PATH=%APPDATA%\npm;C:\Program Files\nodejs;C:\Program Files\Git\cmd;%PATH%

echo ============================================================
echo   Starting OpenCode Agent for Cantonese Kids Studio
echo ============================================================
echo.
call opencode
echo.
echo ============================================================
echo   OpenCode session ended. Press any key to close this window.
echo ============================================================
pause
