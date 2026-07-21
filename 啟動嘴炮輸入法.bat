@echo off
REM VoxProse Windows Launcher
REM Delegates to run_voicetype.bat, which picks the correct Python
REM (.runtime embedded or venv) and runs setup automatically if needed.
call "%~dp0run_voicetype.bat"
