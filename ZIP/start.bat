@echo off
setlocal

REM =========================================
REM   ADMIN PRIVILEGES CHECK
REM =========================================
>nul 2>&1 net session
if %errorlevel% neq 0 (
    echo Requesting administrator elevation...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM =========================================
REM   CHECK REQUIRED ENV VARIABLE
REM =========================================
if "%Run_Crypto_Root_ver%"=="" (
    echo ERROR: Run_Crypto_Root_ver is not defined.
    echo Define it like:
    echo   setx Run_Crypto_Root_ver "C:\CryptoTrader\next_version\crypto-signals\"
    pause
    exit /b 1
)

REM =========================================
REM   BUILD PATHS
REM =========================================
set "BackendDir=%Run_Crypto_Root_ver%backend-engine"
set "FrontendDir=%Run_Crypto_Root_ver%frontend-engine"
set "EngineDir=%Run_Crypto_Root_ver%ml\.venv-ml\Scripts\"

REM convert backslashes to forward slashes for Windows Terminal
set "BackendDir=%BackendDir:\=/%"
set "FrontendDir=%FrontendDir:\=/%"
set "EngineDir=%EngineDir:\=/%"

REM =========================================
REM   START WINDOWS TERMINAL WITH 3 PANES
REM =========================================
echo Starting Windows Terminal with backend, frontend and engine...

wt -w 0 ^
  new-tab --title "backend-engine" --tabColor "#00FFFF" ^
    cmd /k "cd /d \"%BackendDir%\" && npm run dev" ^
  ; split-pane -V --title "frontend-engine" --tabColor "#FFFF00" ^
    cmd /k "cd /d \"%FrontendDir%\" && npm run dev" ^
  ; split-pane -H --title "run scripts" --tabColor "#FF00FF" ^
    cmd /k "cd /d \"%EngineDir%\" && activate.bat" ^

endlocal
