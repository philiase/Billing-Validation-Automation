@echo off
setlocal
cd /d "%~dp0"
python tests\run_tests.py
endlocal
