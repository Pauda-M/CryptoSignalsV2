import os
import math
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, random_split
from dotenv import load_dotenv

# Import the feature matrix loader
from feature_builder.feature_builder_v2 import build_feature_matrix, CFG as FEAT_CFG

# -----------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------
load_dotenv()
MODEL_PATH = os.getenv("TRANSFORMER_MODEL_PATH", "./ml-engine/models/transformer_pg_model_v2.pth")
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

# -----------------------------------------------------------
# Optimized Transformer V2.5 Training Configuration
# -----------------------------------------------------------
@dataclass
class Config:
    window: int = FEAT_CFG.window                     # rolling window = 168
    batch_size: int = 256                             # large batch = stable gradients
    num_epochs: int = 50                              # enough to converge
    d_model: int = 128                                # stronger representation
    nhead: int = 8                                    # ideal for d_model=128
    num_layers: int = 4                               # deeper transformer encoder
    dim_feedforward: int = 256                        # larger MLP inside attention
    dropout: float = 0.2                              # regularization strength
    lr: float = 1e-4                                  # correct learning rate
    weight_decay: float = 1e-5                        # weight decay improves generalization
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    dir_loss_weight: float = 0.7                      # classification weighting


CFG = Config()

# -----------------------------------------------------------
# Dataset based on your 1h aggregated spread
# -----------------------------------------------------------
class SpreadDatasetV2(Dataset):
    def __init__(self, X, y, y_dir, window: int):
        self.X = X
        self.y = y
        self.y_dir = y_dir
        self.window = window
        self.n = X.shape[0]
        self.max_h = 24
        self.valid_n = self.n - self.window - self.max_h
        if self.valid_n <= 0:
            raise RuntimeError("Not enough data to build windows for v2 dataset")

    def __len__(self):
        return self.valid_n

    def __getitem__(self, idx):
        i = idx
        j = i + self.window
        x_win = self.X[i:j, :]
        y_vec = self.y[j, :]
        y_dir_vec = self.y_dir[j, :]
        return torch.from_numpy(x_win), torch.from_numpy(y_vec), torch.from_numpy(y_dir_vec)

# -----------------------------------------------------------
# Optimized Transformer Model (V2.5)
# -----------------------------------------------------------
class SpreadModelV2(nn.Module):
    def __init__(self, d_in, d_model=128, nhead=8, num_layers=4,
                 dim_feedforward=256, dropout=0.2):
        super().__init__()

        self.input_proj = nn.Linear(d_in, d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="gelu"
        )

        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Output heads
        self.fc_mu = nn.Linear(d_model, 3)
        self.fc_log_sigma = nn.Linear(d_model, 3)
        self.fc_dir = nn.Linear(d_model, 3)

    def forward(self, x):
        h = self.input_proj(x)
        h = self.encoder(h)
        h_last = h[:, -1, :]          # last timestep output
        mu = self.fc_mu(h_last)
        log_sigma = self.fc_log_sigma(h_last)
        logits_dir = self.fc_dir(h_last)
        return mu, log_sigma, logits_dir

# -----------------------------------------------------------
# Optimized Loss Functions
# -----------------------------------------------------------
def gaussian_nll(mu, log_sigma, y):
    sigma = torch.exp(log_sigma)
    inv_var = 1.0 / (sigma ** 2 + 1e-8)
    mse_term = (mu - y) ** 2 * inv_var
    log_term = 2 * log_sigma
    return (mse_term + log_term).mean()

def dir_loss_fn(logits_dir, y_dir):
    up = logits_dir.reshape(-1)
    down = torch.zeros_like(up)
    logits2 = torch.stack([down, up], dim=1)
    labels = y_dir.reshape(-1)
    return nn.functional.cross_entropy(logits2, labels)

# -----------------------------------------------------------
# Full Training Loop (with Cosine LR, Gradient Clipping)
# -----------------------------------------------------------
def train_loop_v2():
    print("[v2.5] Loading feature matrix from PostgreSQL...")
    ts, X, y, y_dir = build_feature_matrix()
    print("[v2.5] Feature matrix loaded:", X.shape)

    d_in = X.shape[1]
    ds = SpreadDatasetV2(X, y, y_dir, CFG.window)
    n_total = len(ds)
    n_train = int(n_total * 0.8)
    n_val = n_total - n_train

    train_ds, val_ds = random_split(ds, [n_train, n_val])

    train_dl = DataLoader(train_ds, batch_size=CFG.batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=CFG.batch_size, shuffle=False)

    device = CFG.device
    print(f"[v2.5] Using device: {device}")

    model = SpreadModelV2(
        d_in=d_in,
        d_model=CFG.d_model,
        nhead=CFG.nhead,
        num_layers=CFG.num_layers,
        dim_feedforward=CFG.dim_feedforward,
        dropout=CFG.dropout
    ).to(device)

    optim = torch.optim.AdamW(model.parameters(), lr=CFG.lr, weight_decay=CFG.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=CFG.num_epochs)

    best_val = math.inf

    for epoch in range(1, CFG.num_epochs + 1):
        # ---------------- TRAIN ----------------
        model.train()
        train_loss = 0.0
        for xb, yb, ydirb in train_dl:
            xb = xb.to(device=device, dtype=torch.float32)
            yb = yb.to(device=device, dtype=torch.float32)
            ydirb = ydirb.to(device=device, dtype=torch.long)

            optim.zero_grad()
            mu, log_sigma, logits_dir = model(xb)

            loss_reg = gaussian_nll(mu, log_sigma, yb)
            loss_dir = dir_loss_fn(logits_dir, ydirb)
            loss = loss_reg + CFG.dir_loss_weight * loss_dir

            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

            optim.step()
            train_loss += loss.item() * xb.size(0)

        train_loss /= n_train

        # ---------------- EVAL ----------------
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb, ydirb in val_dl:
                xb = xb.to(device=device, dtype=torch.float32)
                yb = yb.to(device=device, dtype=torch.float32)
                ydirb = ydirb.to(device=device, dtype=torch.long)

                mu, log_sigma, logits_dir = model(xb)
                loss_reg = gaussian_nll(mu, log_sigma, yb)
                loss_dir = dir_loss_fn(logits_dir, ydirb)
                loss = loss_reg + CFG.dir_loss_weight * loss_dir
                val_loss += loss.item() * xb.size(0)

        val_loss /= n_val
        scheduler.step()

        print(f"[v2.5] Epoch {epoch}/{CFG.num_epochs} "
              f"train_loss={train_loss:.6f} val_loss={val_loss:.6f}")

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"[v2.5]  -> Saved best model to {MODEL_PATH}")

    print("[v2.5] Training finished. Best val loss:", best_val)


if __name__ == "__main__":
    train_loop_v2()
