@echo off
title Install Environment
python -m venv venv
call venv\Scripts\activate
echo Installing backend dependencies...
cd backend-engine
pip install -r requirements.txt
cd ..
echo Installing ML dependencies...
cd ml-engine
pip install -r requirements.txt
cd ..
echo Installing frontend dependencies...
cd frontend-engine
npm install
cd ..
echo Initializing database schema...
call venv\Scripts\python init_db.py
echo Done.
pause
