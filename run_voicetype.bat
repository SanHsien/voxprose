@echo off
setlocal
title Starting VoiceType4TW...

rem Force UTF-8 encoding for safety
chcp 65001 >nul

rem Get absolute path of this script
set "BASE_DIR=%~dp0"
set "PYTHONW=%BASE_DIR%venv\Scripts\pythonw.exe"

rem Check if virtual environment exists
if not exist "%PYTHONW%" goto START_SETUP
goto LAUNCH_APP

:START_SETUP
echo [INFO] Python environment not found. 
echo [INFO] Starting setup process...
call "%BASE_DIR%setup_win.bat"

rem Second check
if not exist "%PYTHONW%" goto SETUP_FAIL
goto LAUNCH_APP

:SETUP_FAIL
echo [ERROR] Setup failed or was cancelled. 
pause
exit /b

:LAUNCH_APP
echo [INFO] Launching VoiceType4TW...
echo [INFO] Path: %BASE_DIR%

start "" "%PYTHONW%" "%BASE_DIR%main.py"
exit
