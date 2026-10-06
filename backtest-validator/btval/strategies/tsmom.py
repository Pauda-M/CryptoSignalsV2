import numpy as np
import pandas as pd

from . import Strategy


def signal(prices: pd.Series, lookback: int = 30, vol_window: int = 30,
           target_vol: float = 0.0) -> pd.Series:
    r = np.log(prices).diff()
    mom = r.rolling(lookback).sum()
    sig = np.sign(mom)
    if target_vol > 0:
        vol = r.rolling(vol_window).std()
        sig = sig * (target_vol / vol).clip(upper=1.0)
    return sig.fillna(0.0)


STRATEGY = Strategy(
    name="tsmom",
    signal_fn=signal,
    grid={"lookback": [5, 10, 20, 40, 80]},
    warmup=120,
    mechanism=(
        "Time-series momentum: under-reaction to information and forced flows "
        "(liquidations, funding squeezes). Counterparty: discretionary faders."
    ),
)
