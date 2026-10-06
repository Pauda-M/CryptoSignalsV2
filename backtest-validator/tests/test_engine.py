import numpy as np
import pandas as pd
import pytest

from btval.config import Config
from btval.engine import backtest
from btval.metrics import infer_periods_per_year, metrics


def _px(vals, freq="1D"):
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals), freq=freq, tz="UTC"), dtype=float)


def test_signal_acts_next_bar():
    p = _px([100, 110, 121, 133.1])
    s = pd.Series([1, 1, 1, 1.0], index=p.index)
    bt = backtest(p, s, Config(fee_bps=0, slippage_bps=0))
    assert bt["position"].iloc[0] == 0          # signal at bar 0 not yet tradable
    assert bt["gross"].iloc[1] == pytest.approx(0.10)


def test_short_pnl_is_exact_not_log():
    p = _px([100, 100, 50])
    s = pd.Series([-1, -1, -1.0], index=p.index)
    bt = backtest(p, s, Config(fee_bps=0, slippage_bps=0))
    assert bt["gross"].iloc[2] == pytest.approx(0.5)  # short gains 50%, not -log(0.5)=69%


def test_initial_entry_is_charged():
    p = _px([100, 100, 100])
    s = pd.Series([1, 1, 1.0], index=p.index)
    bt = backtest(p, s, Config(fee_bps=5, slippage_bps=5))
    assert bt["costs"].sum() == pytest.approx(10 / 1e4)


def test_flip_pays_twice():
    p = _px([100] * 4)
    s = pd.Series([1, -1, -1, -1.0], index=p.index)
    bt = backtest(p, s, Config(fee_bps=10, slippage_bps=0))
    assert bt["costs"].iloc[2] == pytest.approx(2 * 10 / 1e4)


def test_lag_zero_refused():
    p = _px([1, 2, 3])
    with pytest.raises(ValueError):
        backtest(p, p * 0, Config(execution_lag=0))


def test_misaligned_signal_refused():
    p = _px([1, 2, 3])
    with pytest.raises(ValueError):
        backtest(p, pd.Series([1, 1, 1.0]), Config())


def test_liquidation_stops_equity():
    p = _px([100, 100, 40, 80])
    s = pd.Series([2.0] * 4, index=p.index)
    bt = backtest(p, s, Config(max_leverage=2, fee_bps=0, slippage_bps=0))
    assert bt["equity"].iloc[-1] == 0
    assert bt["net"].iloc[3] == 0


def test_periods_per_year_inferred_for_4h():
    idx = pd.date_range("2024-01-01", periods=50, freq="4h", tz="UTC")
    assert infer_periods_per_year(idx) == pytest.approx(365 * 6)


def test_metrics_reports_per_period_inputs_for_dsr(rw):
    m = metrics(rw.pct_change().dropna())
    for k in ("sharpe_per_period", "skew", "kurtosis", "n_obs"):
        assert k in m
    assert m["sharpe"] == pytest.approx(m["sharpe_per_period"] * np.sqrt(365), rel=1e-2)
