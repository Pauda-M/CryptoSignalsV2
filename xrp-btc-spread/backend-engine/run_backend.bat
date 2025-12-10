@echo off
set ROOT=%~dp0
cd /D %ROOT%
call ..\venv\Scripts\activate
python run_backend.py
pause
