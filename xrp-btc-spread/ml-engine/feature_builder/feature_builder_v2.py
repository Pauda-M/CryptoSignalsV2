import os
from dataclasses import dataclass
from typing import Tuple, Dict, Any

import numpy as np
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

@dataclass
class FeatureConfig:
    window: int = 168
    min_history: int = 500

CFG = FeatureConfig()

# -----------------------------------------------------------
# DATABASE CONNECTION
# -----------------------------------------------------------
def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set for feature_builder_v2")
    return psycopg2.connect(DATABASE_URL)


# =======================================================
# FETCH RAW HOURLY SPREAD SERIES
# =======================================================
def _fetch_spread_series() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT ts, spread_log, xrp_volume, btc_volume
        FROM xrp_btc_hourly_spread
        ORDER BY ts ASC;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise RuntimeError("xrp_btc_hourly_spread is empty.")

    ts = np.array([r["ts"] for r in rows])
    spread = np.array([float(r["spread_log"]) for r in rows], dtype="float32")
    xrp_v = np.array([float(r["xrp_volume"]) for r in rows], dtype="float32")
    btc_v = np.array([float(r["btc_volume"]) for r in rows], dtype="float32")

    return ts, spread, xrp_v, btc_v


# =======================================================
# FUTURES AGGREGATION
# =======================================================
def _fetch_futures_agg() -> Dict[Any, Dict[str, float]]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT
          date_trunc('hour', tx_time) AS ts_hour,
          symbol,
          side,
          SUM(notional_usd) AS notional
        FROM futures_transactions
        GROUP BY ts_hour, symbol, side
        ORDER BY ts_hour;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    out: Dict[Any, Dict[str, float]] = {}
    for r in rows:
        ts_hour = r["ts_hour"]
        sym = r["symbol"]
        side = r["side"].upper()
        notional = float(r["notional"]) if r["notional"] else 0.0

        d = out.setdefault(ts_hour, {
            "btc_long": 0.0,
            "btc_short": 0.0,
            "xrp_long": 0.0,
            "xrp_short": 0.0,
        })

        if sym == "BTCUSDT":
            if side == "BUY": d["btc_long"] += notional
            else: d["btc_short"] += notional

        elif sym == "XRPUSDT":
            if side == "BUY": d["xrp_long"] += notional
            else: d["xrp_short"] += notional

    return out


# =======================================================
# WALLET AGGREGATION
# =======================================================
def _fetch_wallet_agg() -> Dict[Any, Dict[str, float]]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT
          date_trunc('hour', tx_time) AS ts_hour,
          COUNT(*) AS tx_count,
          COALESCE(SUM(notional_usd),0) AS notional_sum
        FROM wallet_activity
        GROUP BY ts_hour
        ORDER BY ts_hour;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    out: Dict[Any, Dict[str, float]] = {}
    for r in rows:
        out[r["ts_hour"]] = {
            "wallet_tx_count": float(r["tx_count"]),
            "wallet_notional": float(r["notional_sum"]),
        }

    return out


# =======================================================
# SAFE FEATURE BUILDER (FINAL VERSION V3.0)
# =======================================================
def build_feature_matrix():

    # ----------------------------------------------------
    # 1. Load Spread Series
    # ----------------------------------------------------
    ts, spread, xrp_v, btc_v = _fetch_spread_series()
    T = len(spread)

    if T < CFG.min_history:
        raise RuntimeError(f"Not enough history for v2 builder: {T} rows.")

    spread_ret = np.diff(spread, prepend=spread[0])

    # ----------------------------------------------------
    # 2. SAFE Rolling Mean & Std
    # ----------------------------------------------------
    window = 24
    roll_mean = np.zeros(T, "float32")
    roll_std  = np.zeros(T, "float32")

    for i in range(T):
        seg = spread[max(0, i - window + 1): i + 1]
        m = seg.mean()
        s = seg.std()
        roll_mean[i] = m
        roll_std[i]  = s if s > 1e-6 else 1e-6

    # ----------------------------------------------------
    # 3. Normalized Volumes
    # ----------------------------------------------------
    xrp_z = (xrp_v - xrp_v.mean()) / (xrp_v.std() + 1e-6)
    btc_z = (btc_v - btc_v.mean()) / (btc_v.std() + 1e-6)
    vol_ratio = xrp_v / (btc_v + 1e-6)

    # ----------------------------------------------------
    # 4. Futures Aggregation
    # ----------------------------------------------------
    fut = _fetch_futures_agg()
    btc_long  = np.zeros(T, "float32")
    btc_short = np.zeros(T, "float32")
    xrp_long  = np.zeros(T, "float32")
    xrp_short = np.zeros(T, "float32")

    for i, t in enumerate(ts):
        d = fut.get(t)
        if d:
            btc_long[i]  = d["btc_long"]
            btc_short[i] = d["btc_short"]
            xrp_long[i]  = d["xrp_long"]
            xrp_short[i] = d["xrp_short"]

    btc_long_l  = np.log1p(btc_long)
    btc_short_l = np.log1p(btc_short)
    xrp_long_l  = np.log1p(xrp_long)
    xrp_short_l = np.log1p(xrp_short)

    # ----------------------------------------------------
    # 5. Wallet Activity
    # ----------------------------------------------------
    wal = _fetch_wallet_agg()

    wal_tx = np.zeros(T, "float32")
    wal_not = np.zeros(T, "float32")

    for i, t in enumerate(ts):
        d = wal.get(t)
        if d:
            wal_tx[i]  = d["wallet_tx_count"]
            wal_not[i] = d["wallet_notional"]

    wal_tx_l  = np.log1p(wal_tx)
    wal_not_l = np.log1p(wal_not)

    # ----------------------------------------------------
    # 6. ADVANCED FEATURES (SAFE)
    # ----------------------------------------------------
    ts_pd = pd.to_datetime(ts)

    # Realized Volatility
    rv_20 = (
        pd.Series(spread_ret)
        .rolling(20)
        .std()
        .replace(0, 1e-6)
        .fillna(1e-6)
        .astype("float32")
    )

    # Momentum
    mom_1h  = pd.Series(spread).diff(1).fillna(0).astype("float32")
    mom_4h  = pd.Series(spread).diff(4).fillna(0).astype("float32")
    mom_24h = pd.Series(spread).diff(24).fillna(0).astype("float32")

    # EMAs & Trend
    ema_20 = pd.Series(spread).ewm(span=20).mean().astype("float32")
    ema_50 = pd.Series(spread).ewm(span=50).mean().astype("float32")
    trend = (ema_20 - ema_50).astype("float32")

    # Bollinger Bands (SAFE)
    sma_20 = (
        pd.Series(spread)
        .rolling(20).mean()
        .bfill()
        .fillna(0.0)
        .astype("float32")
    )

    std_20 = (
        pd.Series(spread)
        .rolling(20).std()
        .replace(0, 1e-6)
        .bfill()
        .fillna(1e-6)
        .astype("float32")
    )

    z_bb = ((spread - sma_20) / (std_20 + 1e-6)).astype("float32")

    # Velocity & Acceleration
    vel = mom_1h
    acc = mom_1h.diff().fillna(0).astype("float32")

    # Volume Imbalance
    vol_imb = (xrp_v - btc_v).astype("float32")

    # Skew & Kurt (SAFE)
    s_ret = pd.Series(spread_ret)
    skew_20 = (
        s_ret.rolling(20)
        .skew()
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
        .astype("float32")
    )

    kurt_20 = (
        s_ret.rolling(20)
        .kurt()
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
        .astype("float32")
    )

    # ----------------------------------------------------
    # 7. TIME FEATURES (FIXED)
    # ----------------------------------------------------
    hour = ts_pd.hour.astype("float32")
    dow  = ts_pd.dayofweek.astype("float32")

    hour_sin = np.sin(2*np.pi * hour / 24)
    hour_cos = np.cos(2*np.pi * hour / 24)

    dow_sin  = np.sin(2*np.pi * dow / 7)
    dow_cos  = np.cos(2*np.pi * dow / 7)

    # ----------------------------------------------------
    # 8. STACK FEATURES
    # ----------------------------------------------------
    X = np.stack([
        spread, spread_ret,
        roll_mean, roll_std,
        xrp_v, btc_v,
        xrp_z, btc_z,
        vol_ratio,
        btc_long_l, btc_short_l,
        xrp_long_l, xrp_short_l,
        wal_tx_l, wal_not_l,
        rv_20,
        mom_1h, mom_4h, mom_24h,
        ema_20, ema_50, trend,
        z_bb,
        vel, acc,
        vol_imb,
        skew_20, kurt_20,
        hour_sin, hour_cos,
        dow_sin, dow_cos,
    ], axis=1).astype("float32")

    # ----------------------------------------------------
    # 9. TARGETS (1h, 4h, 24h)
    # ----------------------------------------------------
    horizons = [1, 4, 24]
    y = np.zeros((T, 3), "float32")
    y_dir = np.zeros((T, 3), "int64")

    for i in range(T):
        for j, h in enumerate(horizons):
            if i + h < T:
                d = spread[i+h] - spread[i]
                y[i, j] = d
                y_dir[i, j] = 1 if d > 0 else 0

    return ts, X, y, y_dir
