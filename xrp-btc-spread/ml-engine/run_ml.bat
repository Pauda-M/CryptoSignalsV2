@echo off
set ROOT=%~dp0
cd /D %ROOT%
call ..\venv\Scripts\activate
python run_ml.py
pause
