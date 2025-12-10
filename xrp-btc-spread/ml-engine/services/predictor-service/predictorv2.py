import os
import sys
import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# ======================================================
# PATH FIX (works with "ml-engine" hyphen folder)
# ======================================================

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ML_ENGINE_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
PROJECT_ROOT = os.path.dirname(ML_ENGINE_DIR)
sys.path.append(ML_ENGINE_DIR)

# Correct imports
from feature_builder.feature_builder_v2 import build_feature_matrix, CFG as FEAT_CFG
from train_transformer_v2 import SpreadModelV2, CFG as TRAIN_CFG

# ======================================================
# Model paths
# ======================================================
MODEL_AMP = os.path.join(ML_ENGINE_DIR, "models", "transformer_pg_model_v2_amp.pth")
MODEL_FP32 = os.path.join(ML_ENGINE_DIR, "models", "transformer_pg_model_v2.pth")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="Predictor Service V3.8")

# ======================================================
# CORS
# ======================================================
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"[Predictor V3.8] Using device: {DEVICE}")
print(f"[Predictor V3.8] ML_ENGINE_DIR = {ML_ENGINE_DIR}")

# ======================================================
# Load Model
# ======================================================
def load_model():
    try:
        _, X, _, _ = build_feature_matrix()
        d_in = X.shape[1]
        print(f"[Predictor V3.8] Feature count detected: d_in = {d_in}")
    except Exception as e:
        raise RuntimeError(f"Failed to compute feature count: {e}")

    model = SpreadModelV2(d_in=d_in).to(DEVICE)

    if os.path.exists(MODEL_AMP):
        print("[Predictor V3.8] Loading AMP model...")
        state = torch.load(MODEL_AMP, map_location=DEVICE)
        model.load_state_dict(state)
    elif os.path.exists(MODEL_FP32):
        print("[Predictor V3.8] AMP model missing → loading FP32 model...")
        state = torch.load(MODEL_FP32, map_location=DEVICE)
        model.load_state_dict(state)
    else:
        raise RuntimeError("No model file found")

    model.eval()
    return model

MODEL = load_model()

# ======================================================
# Direction decoding
# ======================================================
def decode_direction(logit):
    p_up = float(torch.sigmoid(logit).item())
    p_down = 1 - p_up
    if p_up > 0.55:
        direction = "up"
    elif p_down > 0.55:
        direction = "down"
    else:
        direction = "neutral"
    confidence = max(p_up, p_down)
    return direction, confidence, p_up, p_down

# ======================================================
# Response Models
# ======================================================
class Horizon(BaseModel):
    mu: float
    sigma: float
    direction: str
    confidence: float
    p_up: float
    p_down: float

class PredictionResponse(BaseModel):
    horizon_1h: Horizon
    horizon_4h: Horizon
    horizon_24h: Horizon
    timestamp: str

# ======================================================
# Prediction Endpoint
# ======================================================
@app.get("/api/predictions", response_model=PredictionResponse)
def predict():
    ts, X, y, y_dir = build_feature_matrix()
    window = TRAIN_CFG.window

    x = torch.from_numpy(X[-window:, :]).reshape(1, window, -1).to(DEVICE)

    with torch.inference_mode():
        mu, log_sigma, logits_dir = MODEL(x)

    mu = mu[0].cpu()
    log_sigma = log_sigma[0].cpu()
    logits_dir = logits_dir[0].cpu()

    results = {}
    horizons = ["1h", "4h", "24h"]

    for i, h in enumerate(horizons):
        mu_i = float(mu[i].item())
        sigma_i = float(torch.exp(log_sigma[i]).item())
        direction, conf, p_up, p_down = decode_direction(logits_dir[i])

        results[h] = {
            "mu": mu_i,
            "sigma": sigma_i,
            "direction": direction,
            "confidence": conf,
            "p_up": p_up,
            "p_down": p_down,
        }

    return PredictionResponse(
        horizon_1h = results["1h"],
        horizon_4h = results["4h"],
        horizon_24h = results["24h"],
        timestamp = str(ts[-1])
    )

# ======================================================
# START UVICORN SERVER (the missing part!)
# ======================================================
if __name__ == "__main__":
    print("[Predictor V3.8] Starting API server on port 9101...")
    uvicorn.run(app, host="0.0.0.0", port=9101)
