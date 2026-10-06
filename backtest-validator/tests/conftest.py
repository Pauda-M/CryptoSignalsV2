import numpy as np
import pandas as pd
import pytest

from btval.data import synthetic_prices
from btval.strategies import Strategy


@pytest.fixture
def rw():
    return synthetic_prices(n=1500, seed=11, regime_drift=False)


def _ar1_signal(prices, lb=1):
    return np.sign(np.log(prices).diff(lb)).fillna(0.0)


@pytest.fixture
def ar1_strategy():
    return Strategy("ar1", _ar1_signal, grid={"lb": [1, 2, 3]}, warmup=5, mechanism="planted")
