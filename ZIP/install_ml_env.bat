@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ============================================
echo  ML ENV SETUP FOR MEME XGB MODEL (Python 3.11)
echo ============================================

rem --- Use Python 3.11 explicitly ---
set "PY_CMD=py -3.11"

echo Checking Python 3.11...
%PY_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.11 not found.
    echo Install Python 3.11 and ensure "py -3.11" works.
    pause
    exit /b 1
)

rem --- Create virtualenv ---
if not exist ".venv-ml" (
    echo Creating virtual environment .venv-ml ...
    %PY_CMD% -m venv .venv-ml
) else (
    echo Virtualenv .venv-ml already exists.
)

echo Activating ML virtualenv...
call ".venv-ml\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing ML dependencies for Python 3.11...
python -m pip install xgboost scikit-learn skl2onnx pandas numpy packaging psutil onnxmltools onnx protobuf psycopg2-binary


if errorlevel 1 (
    echo [ERROR] Failed to install ML libraries.
    pause
    exit /b 1
)

echo Verifying imports...
python - << EOF
import xgboost, pandas, skl2onnx, numpy
print("ML environment OK")
EOF

echo ============================================
echo  Python 3.11 ML ENV READY
echo ============================================
pause

endlocal
