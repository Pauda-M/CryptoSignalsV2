@echo off
title Download 3-Year Crypto Market History
call venv\Scripts\activate
python download_history.py
pause
