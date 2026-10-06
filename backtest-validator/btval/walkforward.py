"""Walk-forward: fit on the past, trade the future, roll.

Differences from the usual blog version, each of which changes results:
  * The signal for a test fold is computed with ``warmup`` bars of history
    before the fold. Computing indicators on the test slice alone zeroes the
    first ``warmup`` bars of every fold and makes slow strategies look dead.
  * All folds' OOS signals are stitched into ONE series and backtested once,
    so position carry and switching costs at fold boundaries are real.
  * Folds shorter than the metrics minimum are reported and flagged rather
    than crashing (the blog version with test_days=60 and a 100-obs minimum
    produces zero valid folds).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config
from .engine import backtest
from .metrics import metrics
from .strategies import Strategy


def fit_on(prices: pd.Series, strat: Strategy, cfg: Config) -> tuple[dict, list[dict]]:
    """Grid-search params on ``prices`` by Sharpe. Returns best and the full trial log."""
    trials = []
    for params in strat.param_sets():
        sig = strat.signal(prices, **params)
        bt = backtest(prices, sig, cfg)
        net = bt["net"].iloc[strat.warmup:] if len(bt) > strat.warmup + 10 else bt["net"]
        m = metrics(net, cfg)
        trials.append({"params": params, "sharpe": m.get("sharpe", 0.0),
                       "sharpe_per_period": m.get("sharpe_per_period", 0.0)})
    best = max(trials, key=lambda t: (np.nan_to_num(t["sharpe"], nan=-np.inf)))
    return best["params"], trials


def walk_forward(prices: pd.Series, strat: Strategy, cfg: Config | None = None,
                 train_bars: int = 365, test_bars: int = 90,
                 anchored: bool = False, min_fold_obs: int = 30) -> dict:
    cfg = cfg or Config()
    n = len(prices)
    if train_bars + test_bars > n:
        raise ValueError(f"need >= {train_bars + test_bars} bars, have {n}")

    oos_signal = pd.Series(0.0, index=prices.index)
    in_oos = pd.Series(False, index=prices.index)
    folds = []
    start = 0
    while start + train_bars + test_bars <= n:
        tr_lo = 0 if anchored else start
        tr_hi = start + train_bars
        te_hi = tr_hi + test_bars
        params, _ = fit_on(prices.iloc[tr_lo:tr_hi], strat, cfg)
        hist_lo = max(0, tr_hi - strat.warmup - cfg.execution_lag - 1)
        sig = strat.signal(prices.iloc[hist_lo:te_hi], **params)
        test_idx = prices.index[tr_hi:te_hi]
        oos_signal.loc[test_idx] = sig.loc[test_idx].values
        in_oos.loc[test_idx] = True
        folds.append({"train_start": prices.index[tr_lo], "test_start": test_idx[0],
                      "test_end": test_idx[-1], "params": params})
        start += test_bars

    bt = backtest(prices, oos_signal, cfg)
    oos_net = bt["net"][in_oos]
    for f in folds:
        seg = bt["net"].loc[f["test_start"]:f["test_end"]]
        m = metrics(seg, cfg, min_obs=min_fold_obs)
        f.update({"sharpe": m.get("sharpe", 0.0), "return_pct": m.get("total_return_pct"),
                  "max_dd_pct": m.get("max_drawdown_pct"), "n_obs": m["n_obs"],
                  "low_sample": m.get("low_sample", True)})

    df = pd.DataFrame(folds)
    param_changes = int(sum(a != b for a, b in zip(df["params"], df["params"].iloc[1:])))
    return {
        "folds": df,
        "n_folds": len(df),
        "positive_folds": int((df["sharpe"] > 0).sum()),
        "positive_fold_ratio": round(float((df["sharpe"] > 0).mean()), 3),
        "worst_fold_sharpe": round(float(df["sharpe"].min()), 3),
        "median_fold_sharpe": round(float(df["sharpe"].median()), 3),
        "param_changes": param_changes,  # unstable params = fitting noise
        "oos_metrics": metrics(oos_net, cfg),
        "oos_net": oos_net,
        "oos_backtest": bt[in_oos],
    }
