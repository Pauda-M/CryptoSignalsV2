"""Strategies that lie. The critic must catch every one."""
import numpy as np
import pandas as pd


def peek(prices: pd.Series) -> pd.Series:
    return np.sign(prices.shift(-1) - prices).fillna(0.0)


def centered(prices: pd.Series) -> pd.Series:
    m = prices.rolling(21, center=True).mean()
    return (prices > m).astype(float)


def global_zscore(prices: pd.Series) -> pd.Series:
    z = (prices - prices.mean()) / prices.std()
    return (z < 0).astype(float)


def honest(prices: pd.Series) -> pd.Series:
    m = prices.rolling(50).mean()
    return (prices > m).astype(float)
