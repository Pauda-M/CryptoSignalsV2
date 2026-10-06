from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from .config import Config

SECONDS_PER_YEAR = 365.0 * 86400.0


def infer_periods_per_year(index: pd.DatetimeIndex) -> float:
    """24/7 calendar. Hardcoding 365 on 4H bars understates vol by sqrt(6)."""
    if len(index) < 3:
        raise ValueError("need >= 3 timestamps to infer bar spacing")
    step = pd.Series(index).diff().dropna().dt.total_seconds().median()
    if step <= 0:
        raise ValueError("non-increasing index")
    return SECONDS_PER_YEAR / step


def metrics(net: pd.Series, cfg: Config | None = None, min_obs: int = 30) -> dict:
    """Metrics on per-bar SIMPLE net returns.

    Reports per-period Sharpe, skew and (non-excess) kurtosis because the
    deflated Sharpe needs exactly those — not the annualized number.
    """
    cfg = cfg or Config()
    r = net.dropna()
    n = len(r)
    if n < 3:
        return {"n_obs": n, "error": "insufficient_data"}
    ppy = cfg.periods_per_year or infer_periods_per_year(r.index)

    mu, sd = r.mean(), r.std(ddof=1)
    sr_period = mu / sd if sd > 0 else 0.0
    equity = (1.0 + r).cumprod()
    peak = equity.cummax()
    dd = equity / peak - 1.0
    max_dd = float(dd.min())

    underwater = dd < 0
    runs = underwater.groupby((underwater != underwater.shift()).cumsum()).sum()
    longest_bars = int(runs.max()) if len(runs) else 0

    years = n / ppy
    total = float(equity.iloc[-1])
    cagr = total ** (1 / years) - 1 if years > 0 and total > 0 else -1.0
    ann_vol = sd * np.sqrt(ppy)

    return {
        "n_obs": n,
        "low_sample": n < min_obs,
        "periods_per_year": round(ppy, 2),
        "sharpe": round(float(sr_period * np.sqrt(ppy)), 3),
        "sharpe_per_period": float(sr_period),
        "skew": float(sps.skew(r, bias=False)) if n > 3 else 0.0,
        "kurtosis": float(sps.kurtosis(r, fisher=False, bias=False)) if n > 4 else 3.0,
        "total_return_pct": round((total - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "ann_vol_pct": round(float(ann_vol) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "longest_dd_bars": longest_bars,
        "longest_dd_days": round(longest_bars * 365.0 / ppy, 1),
        "calmar": round(cagr / abs(max_dd), 3) if max_dd < 0 else None,
        "hit_rate": round(float((r[r != 0] > 0).mean()), 3) if (r != 0).any() else None,
    }
