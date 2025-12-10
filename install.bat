@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo   CRYPTO SIGNAL PLATFORM INSTALLER
echo ===========================================
echo.

:: ----------------------------------------------------------
:: CHECK ADMIN PRIVILEGES
:: ----------------------------------------------------------
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo ERROR: Please run this installer as Administrator.
    pause
    exit /b 1
)

:: ----------------------------------------------------------
:: CHECK NODE.JS
:: ----------------------------------------------------------
echo Checking Node.js...
where node >nul 2>&1

if %errorlevel% NEQ 0 (
    echo Node.js not found on this system.
    echo Downloading Node.js LTS installer...

    powershell -Command "Invoke-WebRequest https://nodejs.org/dist/latest-v18.x/node-v18.19.1-x64.msi -OutFile node.msi"

    echo Installing Node.js silently...
    msiexec /i node.msi /quiet ADDLOCAL=ALL

    echo Cleaning up installer...
    del node.msi

    echo Node.js installation completed.
) else (
    echo Node.js found. Continuing...
)

echo.

:: ----------------------------------------------------------
:: INITIALIZE BACKEND ENVIRONMENT
:: ----------------------------------------------------------
echo Initializing backend environment...

if exist backend\.env (
    echo backend/.env already exists.
) else (
    copy backend\.env.example backend\.env >nul
    echo backend/.env created.
)

echo.

:: ----------------------------------------------------------
:: INITIALIZE SIGNAL ENGINE ENVIRONMENT
:: ----------------------------------------------------------
echo Initializing signal-engine environment...

if exist signal-engine\.env (
    echo signal-engine/.env already exists.
) else (
    copy signal-engine\.env.example signal-engine\.env >nul
    echo signal-engine/.env created.
)

echo.

:: ----------------------------------------------------------
:: INSTALL BACKEND DEPENDENCIES
:: ----------------------------------------------------------
echo Installing backend dependencies...
cd backend
call npm install
cd ..

echo.

:: ----------------------------------------------------------
:: INSTALL FRONTEND DEPENDENCIES
:: ----------------------------------------------------------
echo Installing frontend dependencies...
cd frontend
call npm install
cd ..

echo.

:: ----------------------------------------------------------
:: INSTALL SIGNAL ENGINE DEPENDENCIES
:: ----------------------------------------------------------
echo Installing signal-engine dependencies...
cd signal-engine
call npm install
cd ..

echo.

:: ----------------------------------------------------------
:: COMPLETION MESSAGE
:: ----------------------------------------------------------
echo ===========================================
echo   INSTALLATION COMPLETE!
echo -------------------------------------------
echo   START BACKEND:
echo     cd backend
echo     npm run dev
echo.
echo   START FRONTEND:
echo     cd frontend
echo     npm run dev
echo.
echo   START SIGNAL ENGINE:
echo     cd signal-engine
echo     npm start
echo ===========================================

pause
exit /b 0
