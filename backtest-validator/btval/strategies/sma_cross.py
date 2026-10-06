import numpy as np
import pandas as pd

from . import Strategy


def signal(prices: pd.Series, fast: int = 20, slow: int = 100, long_only: bool = True) -> pd.Series:
    if fast >= slow:
        return pd.Series(0.0, index=prices.index)
    f = prices.rolling(fast).mean()
    s = prices.rolling(slow).mean()
    sig = pd.Series(np.where(f > s, 1.0, 0.0 if long_only else -1.0), index=prices.index)
    return sig.where(s.notna(), 0.0)


STRATEGY = Strategy(
    name="sma_cross",
    signal_fn=signal,
    grid={"fast": [10, 20, 50], "slow": [100, 200]},
    warmup=200,
    mechanism=(
        "Trend: slow-moving capital (funds rebalancing, retail chasing late) "
        "extends moves; counterparty is the early mean-reversion seller."
    ),
)
