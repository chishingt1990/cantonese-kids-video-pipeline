@echo off
title OpenCode Web UI - Cantonese Kids Studio
cd /d "%~dp0"
set PATH=%APPDATA%\npm;C:\Program Files\nodejs;C:\Program Files\Git\cmd;%PATH%

echo ============================================================
echo   Starting OpenCode Web Interface (Browser Mode)
echo ============================================================
echo.
call opencode web
pause
