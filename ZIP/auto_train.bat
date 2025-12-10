@echo off
setlocal DISABLEDELAYEDEXPANSION

echo ===============================================
echo        AUTO-TRAIN MEME MODEL PIPELINE
echo ===============================================

PROMPT=$P$G

if not exist ".venv-ml" (
    echo [ERROR] ML venv missing. Run install_ml_env.bat first.
    pause
    exit /b 1
)

echo Activating Python 3.11 ML environment...
call .venv-ml\Scripts\activate.bat

setlocal ENABLEDELAYEDEXPANSION

echo.
echo ===== STEP 1: EXPORT TRAINING DATA FROM POSTGRES =====
pushd ml
python export_training_data.py
if errorlevel 1 (
    echo [ERROR] Training data export failed
    popd
    pause
    exit /b 1
)
popd

echo.
echo ===== STEP 2: TRAIN NEW XGBOOST MODEL =====
pushd ml
python train_meme_xgb.py
if errorlevel 1 (
    echo [ERROR] Model training failed
    popd
    pause
    exit /b 1
)
popd

echo.
echo ===== STEP 3: MODEL UPDATED SUCCESSFULLY =====
echo New model saved to: signal-engine/src/ml_models/meme_xgb.onnx
echo.

echo ===== PIPELINE COMPLETE =====
pause

endlocal
