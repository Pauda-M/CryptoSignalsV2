"""Vectorized backtest engine. Build once, never rewrite.

Conventions (enforced, not suggested):
  * ``prices`` are bar CLOSES indexed by bar CLOSE time.
  * ``signal[t]`` is a target position in [-1, 1] computed only from data
    available at the close of bar t.
  * The position held over bar t is ``signal[t - execution_lag]``.
  * Returns are SIMPLE returns. ``position * log_return`` is wrong for shorts
    and leverage (a short's P&L is -r, not -log(1+r)), so log space is only
    used for compounding the already-netted result.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config


def _validate_inputs(prices: pd.Series, signal: pd.Series) -> None:
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise TypeError("prices must have a DatetimeIndex")
    if not prices.index.is_monotonic_increasing or prices.index.has_duplicates:
        raise ValueError("prices index must be strictly increasing")
    if not signal.index.equals(prices.index):
        raise ValueError("signal index must equal prices index exactly (no silent reindexing)")
    if (prices <= 0).any():
        raise ValueError("prices must be positive")


def backtest(
    prices: pd.Series,
    signal: pd.Series,
    cfg: Config | None = None,
    funding: pd.Series | None = None,
) -> pd.DataFrame:
    """Run the backtest.

    funding: optional per-bar funding rate (fraction, e.g. 0.0001). Longs pay
    positive funding, shorts receive it. Perps only.
    """
    cfg = cfg or Config()
    _validate_inputs(prices, signal)
    if cfg.execution_lag < 1:
        raise ValueError("execution_lag < 1 is look-ahead by construction")

    # THE line: act on a later bar than the one you just saw.
    position = (
        signal.astype(float)
        .shift(cfg.execution_lag)
        .fillna(0.0)
        .clip(-cfg.max_leverage, cfg.max_leverage)
    )
    returns = prices.pct_change().fillna(0.0)
    gross = position * returns

    # Initial entry is turnover too (diff().fillna(0) silently gives it away).
    turnover = position.diff().abs()
    turnover.iloc[0] = abs(position.iloc[0])
    costs = turnover * (cfg.fee_bps + cfg.slippage_bps) / 1e4

    fund = pd.Series(0.0, index=prices.index)
    if funding is not None:
        fund = position * funding.reindex(prices.index).fillna(0.0)

    net = gross - costs - fund
    # A bar that loses >=100% is a liquidation, not a big negative number.
    wiped = net <= -1.0
    if wiped.any():
        first = wiped.idxmax()
        net = net.copy()
        net.loc[first] = -1.0
        net.loc[net.index > first] = 0.0
    equity = cfg.initial_capital * (1.0 + net).cumprod()

    return pd.DataFrame(
        {
            "price": prices,
            "signal": signal,
            "position": position,
            "returns": returns,
            "turnover": turnover,
            "gross": gross,
            "costs": costs,
            "funding": fund,
            "net": net,
            "log_net": np.log1p(net.clip(lower=-1 + 1e-12)),
            "equity": equity,
        }
    )
