"""Size for the path, not the destination."""
from __future__ import annotations

import numpy as np
import pandas as pd


def position_size(capital: float, entry: float, stop: float, risk_pct: float = 0.01,
                  max_position_pct: float = 0.20, fee_bps: float = 0.0,
                  slippage_bps: float = 0.0) -> dict:
    """Fixed-fractional sizing to a stop.

    Costs on entry and exit are part of the loss when the stop hits; ignoring
    them makes a 1% risk budget a 1.1-1.3% one on tight stops.
    """
    if capital <= 0 or entry <= 0 or stop <= 0:
        raise ValueError("capital, entry and stop must be positive")
    if not 0 < risk_pct < 1:
        raise ValueError("risk_pct must be in (0, 1)")
    per_side = (fee_bps + slippage_bps) / 1e4
    risk_per_unit = abs(entry - stop) + per_side * (entry + stop)
    if abs(entry - stop) == 0:
        raise ValueError("stop cannot equal entry")
    units = capital * risk_pct / risk_per_unit
    capped = False
    if units * entry > capital * max_position_pct:
        units = capital * max_position_pct / entry
        capped = True
    notional = units * entry
    return {
        "side": "long" if stop < entry else "short",
        "units": round(units, 8),
        "notional": round(notional, 2),
        "pct_of_capital": round(notional / capital * 100, 2),
        "loss_if_stopped": round(units * risk_per_unit, 2),
        "loss_if_stopped_pct": round(units * risk_per_unit / capital * 100, 3),
        "capped_by_max_position": capped,
    }


def prob_losing_streak(loss_prob: float, n_trades: int, k: int) -> float:
    """P(at least one run of >= k consecutive losses in n_trades)."""
    if k <= 0:
        return 1.0
    if k > n_trades:
        return 0.0
    # state = current run length (0..k-1); absorbing at k
    dist = np.zeros(k)
    dist[0] = 1.0
    hit = 0.0
    for _ in range(n_trades):
        new = np.zeros(k)
        new[0] = dist.sum() * (1 - loss_prob)
        new[1:] = dist[:-1] * loss_prob
        hit += dist[-1] * loss_prob
        dist = new
    return float(hit)


def streak_table(win_rate: float, trades_per_year: int, risk_pcts=(0.005, 0.01, 0.02, 0.05),
                 streaks=(6, 8, 10, 12, 15)) -> dict:
    """What a losing streak does to the account, and how often you should expect it."""
    q = 1 - win_rate
    rows = []
    for k in streaks:
        p = prob_losing_streak(q, trades_per_year, k)
        rows.append({
            "streak": k,
            "p_at_least_once_per_year": round(p, 4),
            "drawdown_pct": {f"{r*100:g}%": round((1 - (1 - r) ** k) * 100, 1) for r in risk_pcts},
        })
    return {"win_rate": win_rate, "trades_per_year": trades_per_year, "rows": rows}


def kelly_from_returns(net: pd.Series, fraction: float = 0.5) -> dict:
    """Continuous Kelly leverage mu/sigma^2 on per-bar returns, scaled by `fraction`.

    Full Kelly on an estimated mean is a bet that your backtest is exactly
    right. It is not. Half-Kelly or less.
    """
    r = net.dropna()
    var = float(r.var(ddof=1))
    if var <= 0:
        return {"kelly_leverage": 0.0, "recommended_leverage": 0.0}
    k = float(r.mean() / var)
    return {"kelly_leverage": round(k, 3), "fraction": fraction,
            "recommended_leverage": round(max(0.0, k * fraction), 3)}
