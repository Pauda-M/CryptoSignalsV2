
import os
from dataclasses import dataclass
from typing import Tuple, Dict, Any

import numpy as np
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

@dataclass
class FeatureConfig:
    window: int = 168
    min_history: int = 500

CFG = FeatureConfig()

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set for feature_builder_v2")
    return psycopg2.connect(DATABASE_URL)

def _fetch_spread_series() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        SELECT ts, spread_log, xrp_volume, btc_volume
        FROM xrp_btc_hourly_spread
        ORDER BY ts ASC;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        raise RuntimeError("xrp_btc_hourly_spread is empty")

    ts = np.array([r["ts"] for r in rows])
    spread = np.array([float(r["spread_log"]) for r in rows], dtype="float32")
    xrp_v = np.array([float(r["xrp_volume"]) for r in rows], dtype="float32")
    btc_v = np.array([float(r["btc_volume"]) for r in rows], dtype="float32")
    return ts, spread, xrp_v, btc_v

def _fetch_futures_agg() -> Dict[Any, Dict[str, float]]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        SELECT
          date_trunc('hour', tx_time) AS ts_hour,
          symbol,
          side,
          SUM(notional_usd) AS notional
        FROM futures_transactions
        GROUP BY ts_hour, symbol, side
        ORDER BY ts_hour;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    agg: Dict[Any, Dict[str, float]] = {}
    for r in rows:
        ts_hour = r["ts_hour"]
        sym = r["symbol"]
        side = r["side"].upper()
        notional = float(r["notional"]) if r["notional"] is not None else 0.0
        d = agg.setdefault(ts_hour, {
            "btc_long": 0.0,
            "btc_short": 0.0,
            "xrp_long": 0.0,
            "xrp_short": 0.0,
        })
        if sym == "BTCUSDT":
            if side == "BUY":
                d["btc_long"] += notional
            else:
                d["btc_short"] += notional
        elif sym == "XRPUSDT":
            if side == "BUY":
                d["xrp_long"] += notional
            else:
                d["xrp_short"] += notional
    return agg

def _fetch_wallet_agg() -> Dict[Any, Dict[str, float]]:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        SELECT
          date_trunc('hour', tx_time) AS ts_hour,
          COUNT(*) AS tx_count,
          COALESCE(SUM(notional_usd),0) AS notional_sum
        FROM wallet_activity
        GROUP BY ts_hour
        ORDER BY ts_hour;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    agg: Dict[Any, Dict[str, float]] = {}
    for r in rows:
        ts_hour = r["ts_hour"]
        agg[ts_hour] = {
            "wallet_tx_count": float(r["tx_count"]),
            "wallet_notional": float(r["notional_sum"]),
        }
    return agg

def build_feature_matrix() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ts, spread, xrp_v, btc_v = _fetch_spread_series()
    T = len(spread)
    if T < CFG.min_history:
        raise RuntimeError(f"Not enough history for training v2: {T} < {CFG.min_history}")

    spread_ret = np.diff(spread, prepend=spread[0])
    window_vol = 24
    roll_mean = np.zeros_like(spread)
    roll_std = np.zeros_like(spread)
    for i in range(T):
        start = max(0, i - window_vol + 1)
        seg = spread[start:i+1]
        roll_mean[i] = seg.mean()
        roll_std[i] = seg.std() if seg.std() > 1e-8 else 1e-8

    xrp_z = (xrp_v - xrp_v.mean()) / (xrp_v.std() + 1e-8)
    btc_z = (btc_v - btc_v.mean()) / (btc_v.std() + 1e-8)
    vol_ratio = xrp_v / (btc_v + 1e-8)

    fut = _fetch_futures_agg()
    btc_long = np.zeros_like(spread)
    btc_short = np.zeros_like(spread)
    xrp_long = np.zeros_like(spread)
    xrp_short = np.zeros_like(spread)
    for i, t in enumerate(ts):
        d = fut.get(t, None)
        if d:
            btc_long[i] = d["btc_long"]
            btc_short[i] = d["btc_short"]
            xrp_long[i] = d["xrp_long"]
            xrp_short[i] = d["xrp_short"]

    wal = _fetch_wallet_agg()
    wal_tx = np.zeros_like(spread)
    wal_notional = np.zeros_like(spread)
    for i, t in enumerate(ts):
        d = wal.get(t, None)
        if d:
            wal_tx[i] = d["wallet_tx_count"]
            wal_notional[i] = d["wallet_notional"]

    btc_long_l = np.log1p(btc_long)
    btc_short_l = np.log1p(btc_short)
    xrp_long_l = np.log1p(xrp_long)
    xrp_short_l = np.log1p(xrp_short)
    wal_tx_l = np.log1p(wal_tx)
    wal_notional_l = np.log1p(wal_notional)

    import pandas as pd
    ts_pd = pd.to_datetime(ts)
    hour = ts_pd.dt.hour.values.astype("float32")
    dayofweek = ts_pd.dt.dayofweek.values.astype("float32")
    hour_sin = np.sin(2 * np.pi * hour / 24.0)
    hour_cos = np.cos(2 * np.pi * hour / 24.0)
    dow_sin = np.sin(2 * np.pi * dayofweek / 7.0)
    dow_cos = np.cos(2 * np.pi * dayofweek / 7.0)

    X = np.stack(
        [
            spread,
            spread_ret,
            roll_mean,
            roll_std,
            xrp_v,
            btc_v,
            xrp_z,
            btc_z,
            vol_ratio,
            btc_long_l,
            btc_short_l,
            xrp_long_l,
            xrp_short_l,
            wal_tx_l,
            wal_notional_l,
            hour_sin,
            hour_cos,
            dow_sin,
            dow_cos,
        ],
        axis=1,
    ).astype("float32")

    horizons = [1, 4, 24]
    H = len(horizons)
    y = np.zeros((T, H), dtype="float32")
    y_dir = np.zeros((T, H), dtype="int64")
    for i in range(T):
        for j, h in enumerate(horizons):
            if i + h < T:
                delta = spread[i + h] - spread[i]
                y[i, j] = delta
                y_dir[i, j] = 1 if delta > 0 else 0

    return ts, X, y, y_dir
