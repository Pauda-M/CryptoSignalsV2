"""Live monitoring against kill conditions fixed BEFORE deployment.

A 30-bar live Sharpe compared to half the backtest Sharpe fires on noise:
the standard error of a 30-day annualized Sharpe is ~3.5. Here decay is a
statistical test, and the window has a floor.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import probabilistic_sharpe


def kill_conditions(bt_metrics: dict, dd_multiple: float = 1.5, decay_fraction: float = 0.5,
                    min_window: int = 90, alpha: float = 0.05) -> dict:
    return {
        "expected_sr_per_period": bt_metrics["sharpe_per_period"],
        "backtest_max_dd_pct": bt_metrics["max_drawdown_pct"],
        "max_dd_pct_limit": round(bt_metrics["max_drawdown_pct"] * dd_multiple, 2),
        "decay_fraction": decay_fraction,
        "min_window": min_window,
        "alpha": alpha,
    }


def health_check(live_net: pd.Series, kill: dict, window: int | None = None) -> dict:
    r = live_net.dropna()
    window = max(window or kill["min_window"], kill["min_window"])
    recent = r.tail(window)
    equity = (1 + r).cumprod()
    dd = float(equity.iloc[-1] / equity.cummax().iloc[-1] - 1) if len(r) else 0.0

    alerts, notes = [], []
    if dd * 100 < kill["max_dd_pct_limit"]:
        alerts.append("DRAWDOWN_EXCEEDED")

    live_sr = None
    p_ok = None
    if len(recent) < kill["min_window"]:
        notes.append(f"only {len(recent)} live bars; Sharpe decay test needs {kill['min_window']}")
    else:
        sd = recent.std(ddof=1)
        live_sr = float(recent.mean() / sd) if sd > 0 else 0.0
        bench = kill["expected_sr_per_period"] * kill["decay_fraction"]
        # P(true live SR >= decayed benchmark). Low = the edge is gone.
        p_ok = probabilistic_sharpe(live_sr, len(recent), sr_benchmark=bench)
        if p_ok < kill["alpha"]:
            alerts.append("SHARPE_DECAY")
    return {
        "live_bars": len(r),
        "live_sr_per_period": live_sr,
        "p_live_sr_above_decayed_benchmark": None if p_ok is None else round(p_ok, 4),
        "current_dd_pct": round(dd * 100, 2),
        "alerts": alerts,
        "notes": notes,
        "action": "HALT" if alerts else "CONTINUE",
    }
