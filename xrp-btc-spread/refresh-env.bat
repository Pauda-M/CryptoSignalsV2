@echo off
title Refresh Environments
echo Removing existing venv...
if exist venv rmdir /S /Q venv
python -m venv venv
call venv\Scripts\activate
echo Reinstalling backend dependencies...
cd backend-engine
pip install -r requirements.txt
cd ..
echo Reinstalling ML dependencies...
cd ml-engine
pip install -r requirements.txt
cd ..
echo Reinstalling frontend dependencies...
cd frontend-engine
npm install
cd ..
echo Refresh complete.
pause
