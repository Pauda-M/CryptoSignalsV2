import os
import math
import time
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, random_split
from dotenv import load_dotenv

from torch.amp import autocast, GradScaler

from feature_builder.feature_builder_v2 import build_feature_matrix, CFG as FEAT_CFG

load_dotenv()

# AMP MODEL SAVE PATH (new file to avoid overwriting v3.5)
MODEL_PATH_AMP = "./ml-engine/models/transformer_pg_model_v2_amp.pth"
os.makedirs(os.path.dirname(MODEL_PATH_AMP), exist_ok=True)


# ============================================================
# CONFIG
# ============================================================
@dataclass
class Config:
    window: int = FEAT_CFG.window
    batch_size: int = 192
    num_epochs: int = 50

    d_model: int = 128
    nhead: int = 4
    num_layers: int = 3
    dim_feedforward: int = 256
    dropout: float = 0.15

    lr: float = 1e-5
    weight_decay: float = 1e-6

    # CUDA
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    # Loss mixing weight
    dir_loss_weight: float = 0.7


CFG = Config()


# ============================================================
# DATASET
# ============================================================
class SpreadDatasetV2(Dataset):
    def __init__(self, X, y, y_dir, window):
        self.X = X
        self.y = y
        self.y_dir = y_dir
        self.window = window

        self.n = X.shape[0]
        self.max_h = 24
        self.valid_n = self.n - window - self.max_h

    def __len__(self):
        return self.valid_n

    def __getitem__(self, idx):
        i = idx
        j = i + self.window
        return (
            torch.from_numpy(self.X[i:j, :]),
            torch.from_numpy(self.y[j, :]),
            torch.from_numpy(self.y_dir[j, :]),
        )


# ============================================================
# MODEL (stabilized transformer)
# ============================================================
class SpreadModelV2(nn.Module):
    def __init__(self, d_in, d_model=128, nhead=4,
                 num_layers=3, dim_feedforward=256, dropout=0.15):
        super().__init__()

        self.input_proj = nn.Linear(d_in, d_model)

        # FP32-safe normalization
        self.pre_norm = nn.LayerNorm(d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)

        self.fc_mu = nn.Linear(d_model, 3)
        self.fc_log_sigma = nn.Sequential(
            nn.Linear(d_model, 3),
            nn.Tanh()              # bound log_sigma to [-1,1]
        )
        self.fc_dir = nn.Linear(d_model, 3)

    def forward(self, x):
        # FP32 region (NO autocast)
        with torch.amp.autocast("cuda", enabled=False):
            h = self.input_proj(x)                  # float32
            h = self.pre_norm(h)                    # float32
            h = (h - h.mean(dim=1, keepdim=True)) / (h.std(dim=1, keepdim=True) + 1e-6)

        # FP16 region = FAST
        with autocast(device_type="cuda", dtype=torch.float16):
            h = self.encoder(h)                     # float16
            last = h[:, -1, :]
            mu = self.fc_mu(last)
            log_sigma = self.fc_log_sigma(last)
            logits_dir = self.fc_dir(last)

        return mu, log_sigma, logits_dir


# ============================================================
# LOSSES (always FP32 — stable)
# ============================================================
def gaussian_nll(mu, log_sigma, y):
    # Convert back to FP32 (vital)
    mu = mu.float()
    log_sigma = log_sigma.float()
    y = y.float()

    log_sigma = log_sigma.clamp(min=-3.0, max=3.0)
    sigma = torch.exp(log_sigma)
    inv_var = 1.0 / (sigma ** 2 + 1e-6)

    return ((mu - y)**2 * inv_var + 2 * log_sigma).mean()


def dir_loss_fn(logits_dir, y_dir):
    logits_dir = logits_dir.float()
    y_dir = y_dir.long()

    logits = torch.stack(
        [
            torch.zeros_like(logits_dir),
            logits_dir
        ],
        dim=-1
    )
    logits = logits.reshape(-1, 2)
    labels = y_dir.reshape(-1)

    return nn.functional.cross_entropy(logits, labels)


# ============================================================
# TRAINING LOOP (HYBRID AMP — V3.7)
# ============================================================
def train_loop_v2():
    print("[v3.7 HYBRID-AMP] Loading feature matrix...")
    ts, X, y, y_dir = build_feature_matrix()
    print(f"[v3.7 HYBRID-AMP] Feature matrix shape: {X.shape}")
    device = CFG.device
    print(f"[v3.7 HYBRID-AMP] Using device: {device}")

    d_in = X.shape[1]

    ds = SpreadDatasetV2(X, y, y_dir, CFG.window)
    total = len(ds)
    n_train = int(total * 0.8)
    n_val = total - n_train

    train_ds, val_ds = random_split(ds, [n_train, n_val])
    train_dl = DataLoader(train_ds, CFG.batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(val_ds, CFG.batch_size, shuffle=False)

    model = SpreadModelV2(
        d_in=d_in,
        d_model=CFG.d_model,
        nhead=CFG.nhead,
        num_layers=CFG.num_layers,
        dim_feedforward=CFG.dim_feedforward,
        dropout=CFG.dropout
    ).to(device)

    optim = torch.optim.AdamW(
        model.parameters(),
        lr=CFG.lr,
        weight_decay=CFG.weight_decay
    )

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optim, T_max=CFG.num_epochs
    )

    scaler = GradScaler(device="cuda")

    best_val = math.inf

    for epoch in range(1, CFG.num_epochs + 1):
        model.train()
        train_loss = 0.0
        t0 = time.time()

        for xb, yb, ydirb in train_dl:
            xb, yb, ydirb = xb.to(device), yb.to(device), ydirb.to(device)

            optim.zero_grad()

            # FP16 encoder + FP32 normalization
            with autocast(device_type="cuda", dtype=torch.float16):
                mu, log_sigma, logits_dir = model(xb)

            # Compute losses in FP32
            loss_reg = gaussian_nll(mu, log_sigma, yb)
            loss_dir = dir_loss_fn(logits_dir, ydirb)
            loss = loss_reg + CFG.dir_loss_weight * loss_dir

            scaler.scale(loss).backward()

            # Before optimizer step, unscale and clip
            scaler.unscale_(optim)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.25)

            scaler.step(optim)
            scaler.update()

            train_loss += loss.item() * xb.size(0)

        train_loss /= n_train

        # Validation
        model.eval()
        val_loss = 0.0

        with torch.no_grad():
            for xb, yb, ydirb in val_dl:
                xb, yb, ydirb = xb.to(device), yb.to(device), ydirb.to(device)

                with autocast(device_type="cuda", dtype=torch.float16):
                    mu, log_sigma, logits_dir = model(xb)

                loss_reg = gaussian_nll(mu, log_sigma, yb)
                loss_dir = dir_loss_fn(logits_dir, ydirb)
                loss = loss_reg + CFG.dir_loss_weight * loss_dir

                val_loss += loss.item() * xb.size(0)

        val_loss /= n_val
        scheduler.step()

        dt = time.time() - t0
        eta = dt * (CFG.num_epochs - epoch) / 60

        print(f"[v3.7 HYBRID-AMP] Epoch {epoch}/{CFG.num_epochs} "
              f"train={train_loss:.6f}  val={val_loss:.6f}  | {dt:.2f}s  ETA={eta:.1f} min")

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), MODEL_PATH_AMP)
            print(f"[v3.7 HYBRID-AMP]  -> Saved AMP model to {MODEL_PATH_AMP}")


if __name__ == "__main__":
    train_loop_v2()
