@echo off
setlocal DISABLEDELAYEDEXPANSION

echo ============================================
echo     TRAIN MEME XGB MODEL (Python 3.11)
echo ============================================

REM --- Force clean prompt (prevents "(venv)" errors) ---
PROMPT=$P$G

REM --- Ensure ML virtualenv exists ---
if not exist ".venv-ml" (
    echo [ERROR] ML environment not found.
    echo Run install_ml_env.bat first.
    pause
    exit /b 1
)

echo Activating ML environment...
call ".venv-ml\Scripts\activate.bat"

REM --- Now we can safely re-enable delayed expansion ---
setlocal ENABLEDELAYEDEXPANSION

pushd "ml"

if not exist "meme_training.csv" (
    echo.
    echo [WARN] meme_training.csv NOT FOUND.
    echo Creating a TEMPLATE dataset...

    (
        echo alpha_target,recency,social_score,marketCap,liquidityUSD,volumeUSD,holders,tradeCount,velocity
        echo 0.12,0.55,0.61,1500000,80000,120000,780,42,0.28
        echo -0.08,0.22,0.48,900000,40000,65000,320,18,-0.14
    ) > meme_training.csv

    echo Template created at: ml\meme_training.csv
    echo Edit this file, then re-run train_meme_xgb.bat
    echo.
    pause
    popd
    exit /b 0
)

echo Running training script...
python train_meme_xgb.py

if errorlevel 1 (
    echo [ERROR] Training failed.
    popd
    pause
    exit /b 1
)

popd

echo ============================================
echo   TRAINING COMPLETED — ONNX MODEL UPDATED
echo ============================================
pause

endlocal
