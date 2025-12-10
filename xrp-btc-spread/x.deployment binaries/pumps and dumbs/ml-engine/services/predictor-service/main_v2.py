
#!/usr/bin/env python3
import sys
import os
from typing import List

from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel

import torch
import numpy as np
from dotenv import load_dotenv

from ml-engine.feature_builder_v2 import build_feature_matrix, CFG as FEAT_CFG
from ml-engine.train_transformer_v2 import SpreadModelV2

load_dotenv()
MODEL_PATH = os.getenv("TRANSFORMER_MODEL_PATH", "./ml-engine/models/transformer_pg_model_v2.pth")

app = FastAPI(title="Predictor Service V2")

class Prediction(BaseModel):
    horizon: str
    mu: float
    sigma: float
    prob_up: float
    prob_down: float

device = "cuda" if torch.cuda.is_available() else "cpu"
model = None

def load_latest_window():
    ts, X, y, y_dir = build_feature_matrix()
    if X.shape[0] < FEAT_CFG.window:
        raise RuntimeError("Not enough history for v2 prediction window")
    x_win = X[-FEAT_CFG.window:, :]
    x_win = x_win[None, :, :]
    return x_win

def ensure_model(d_in=None):
    global model
    if model is not None:
        return model
    if d_in is None:
        _, X_tmp, _, _ = build_feature_matrix()
        d_in = X_tmp.shape[1]
    m = SpreadModelV2(d_in=d_in)
    if os.path.exists(MODEL_PATH):
        try:
            state = torch.load(MODEL_PATH, map_location=device)
            m.load_state_dict(state)
            print("[v2] Loaded SpreadModelV2 from", MODEL_PATH)
        except Exception as e:
            print("[v2] Could not load model, using untrained weights:", e)
    else:
        print("[v2] Model path does not exist, using untrained weights.")
    m.to(device)
    m.eval()
    model = m
    return model

@app.get("/health")
def health():
    return {"status": "ok", "service": "Predictor Service V2"}

@app.get("/predict_v2", response_model=List[Prediction])
def predict_v2():
    x = load_latest_window()
    d_in = x.shape[2]
    m = ensure_model(d_in)
    x_t = torch.tensor(x, dtype=torch.float32, device=device)
    with torch.no_grad():
        mu_t, log_sigma_t, logits_dir = m(x_t)
    mu = mu_t[0].cpu().numpy()
    sigma = np.exp(log_sigma_t[0].cpu().numpy())
    logits = logits_dir[0].cpu().numpy()
    up = logits
    down = np.zeros_like(up)
    logits2 = np.stack([down, up], axis=1)
    exp_logits = np.exp(logits2 - logits2.max(axis=1, keepdims=True))
    probs2 = exp_logits / exp_logits.sum(axis=1, keepdims=True)
    prob_up = probs2[:, 1]
    prob_down = probs2[:, 0]

    horizons = ["1h", "4h", "24h"]
    out: List[Prediction] = []
    for i, h in enumerate(horizons):
        mval = float(mu[i])
        sval = float(sigma[i]) if float(sigma[i]) > 1e-8 else 1e-3
        pu = float(max(min(prob_up[i], 0.999), 0.001))
        pd = float(1.0 - pu)
        out.append(Prediction(horizon=h, mu=mval, sigma=sval, prob_up=pu, prob_down=pd))
    return out

@app.get("/predict", response_model=List[Prediction])
def predict_default():
    return predict_v2()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    uvicorn.run("main_v2:app", host="0.0.0.0", port=port)
