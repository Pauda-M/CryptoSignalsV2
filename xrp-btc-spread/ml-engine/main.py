#!/usr/bin/env python3
"""
Auto-switching Predictor Service
- Uses ML v2 if available AND working
- Falls back to ML v1 if v2 is missing or fails
- Never crashes
"""

import os
import sys
from typing import List

from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel

import numpy as np
import torch
import torch.nn as nn
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
V2_MODEL_PATH = "../models/transformer_pg_model_v2.pth"
V1_MODEL_PATH = "./ml_engine/models/transformer_pg_model.pth"

app = FastAPI(title="Predictor Service Auto-Fallback")

# ==================================================
# SHARED UTILITIES
# ==================================================

def get_conn():
    return psycopg2.connect(DATABASE_URL)

class Prediction(BaseModel):
    horizon: str
    mu: float
    sigma: float
    prob_up: float
    prob_down: float

device = "cuda" if torch.cuda.is_available() else "cpu"


# ==================================================
# V1 MODEL + FEATURES
# ==================================================

class SimpleSpreadModel(nn.Module):
    def __init__(self, d_in=3, d_model=64, nhead=4, num_layers=2, dim_feedforward=128, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(d_in, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=False,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc_mu = nn.Linear(d_model, 3)
        self.fc_log_sigma = nn.Linear(d_model, 3)

    def forward(self, x):
        h = self.input_proj(x)
        h = self.encoder(h)
        h_last = h[-1, :, :]
        mu = self.fc_mu(h_last)
        log_sigma = self.fc_log_sigma(h_last)
        return mu, log_sigma


def load_last_window_v1(window=168):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT ts, spread_log, xrp_volume, btc_volume
        FROM xrp_btc_hourly_spread
        ORDER BY ts DESC
        LIMIT %s;
    """, (window,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise RuntimeError("Spread table empty")

    rows = list(reversed(rows))
    spread = np.array([float(r["spread_log"]) for r in rows], dtype="float32")
    xrp_v = np.array([float(r["xrp_volume"]) for r in rows], dtype="float32")
    btc_v = np.array([float(r["btc_volume"]) for r in rows], dtype="float32")

    xrp_z = (xrp_v - xrp_v.mean()) / (xrp_v.std() + 1e-8)
    btc_z = (btc_v - btc_v.mean()) / (btc_v.std() + 1e-8)

    X = np.stack([spread, xrp_z, btc_z], axis=1)
    return X[:, None, :]


def predict_v1():
    X = load_last_window_v1()
    x_t = torch.tensor(X, dtype=torch.float32, device=device)

    global v1_model
    with torch.no_grad():
        mu_t, log_sigma_t = v1_model(x_t)

    mu = mu_t[0].cpu().numpy()
    sigma = np.exp(log_sigma_t[0].cpu().numpy())

    # original heuristic
    out = []
    horizons = ["1h", "4h", "24h"]
    for i, h in enumerate(horizons):
        m = float(mu[i])
        s = float(sigma[i]) if float(sigma[i]) > 1e-8 else 1e-3
        score = m / (4 * s)
        score = max(min(score, 0.4), -0.4)
        pu = 0.5 + score
        pd = 1 - pu
        out.append(Prediction(horizon=h, mu=m, sigma=s, prob_up=pu, prob_down=pd))
    return out


# ==================================================
# LOAD V1 MODEL
# ==================================================

v1_model = SimpleSpreadModel().to(device)
if os.path.exists(V1_MODEL_PATH):
    try:
        v1_model.load_state_dict(torch.load(V1_MODEL_PATH, map_location=device))
        print("[AUTO] Loaded V1 model")
    except Exception as e:
        print("[AUTO] Could not load V1 model, using random weights:", e)
v1_model.eval()


# ==================================================
# V2 MODEL + FEATURES
# ==================================================

# Import here so v1 fallback works even if v2 imports fail
try:
    from feature_builder.feature_builder_v2 import build_feature_matrix, CFG as FEAT_CFG
    from ml_engine.train_transformer_v2 import SpreadModelV2
    v2_import_ok = True
except Exception as e:
    print("[AUTO] WARNING: V2 imports failed:", e)
    v2_import_ok = False
    SpreadModelV2 = None

v2_model = None

def load_v2_model():
    global v2_model
    if v2_model is not None:
        return v2_model

    if not v2_import_ok:
        return None

    if not os.path.exists(V2_MODEL_PATH):
        print("[AUTO] V2 model not found → fallback to V1")
        return None

    try:
        ts, X_tmp, _, _ = build_feature_matrix()
        d_in = X_tmp.shape[1]
        m = SpreadModelV2(d_in=d_in)
        m.load_state_dict(torch.load(V2_MODEL_PATH, map_location=device))
        m.to(device)
        m.eval()
        v2_model = m
        print("[AUTO] Loaded V2 model")
        return m
    except Exception as e:
        print("[AUTO] ERROR loading V2 model:", e)
        return None


def predict_v2():
    ts, X, y, y_dir = build_feature_matrix()
    if X.shape[0] < FEAT_CFG.window:
        raise RuntimeError("Not enough history for V2")

    x_win = X[-FEAT_CFG.window:, :]
    x_win = x_win[None, :, :]
    x_t = torch.tensor(x_win, dtype=torch.float32, device=device)

    m = load_v2_model()
    if m is None:
        raise RuntimeError("V2 model unavailable")

    with torch.no_grad():
        mu_t, log_sigma_t, logits_dir = m(x_t)

    mu = mu_t[0].cpu().numpy()
    sigma = np.exp(log_sigma_t[0].cpu().numpy())

    # convert logits to prob_up
    logits = logits_dir[0].cpu().numpy()
    down = np.zeros_like(logits)
    logits2 = np.stack([down, logits], axis=1)
    exp_logits = np.exp(logits2 - logits2.max(axis=1, keepdims=True))
    probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)

    horizons = ["1h", "4h", "24h"]
    out = []
    for i, h in enumerate(horizons):
        out.append(Prediction(
            horizon=h,
            mu=float(mu[i]),
            sigma=float(sigma[i]),
            prob_up=float(probs[i, 1]),
            prob_down=float(probs[i, 0])
        ))
    return out


# ==================================================
# PUBLIC ENDPOINTS
# ==================================================

@app.get("/health")
def health():
    if v2_import_ok and os.path.exists(V2_MODEL_PATH):
        return {"status": "ok", "model": "v2"}
    return {"status": "ok", "model": "v1"}


@app.get("/predict", response_model=List[Prediction])
def predict():
    """
    Auto-switch logic:
    1. Try V2
    2. If ANY error occurs → fallback to V1
    """
    try:
        if v2_import_ok and os.path.exists(V2_MODEL_PATH):
            return predict_v2()
    except Exception as e:
        print("[AUTO] V2 failed, falling back to V1:", e)

    return predict_v1()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    uvicorn.run("main:app", host="0.0.0.0", port=port)
