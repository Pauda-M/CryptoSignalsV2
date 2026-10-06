import numpy as np
import pandas as pd
import pytest

from btval.health import health_check, kill_conditions
from btval.sizing import kelly_from_returns, position_size, prob_losing_streak


def test_risk_includes_costs():
    out = position_size(10_000, 100, 98, risk_pct=0.01, max_position_pct=1.0, fee_bps=5, slippage_bps=5)
    assert out["loss_if_stopped"] == pytest.approx(100, rel=1e-6)
    assert out["notional"] < 10_000 * 0.01 / 0.02 * 1.0


def test_cap_applies_and_short_side():
    out = position_size(10_000, 100, 100.1, risk_pct=0.01)
    assert out["capped_by_max_position"] and out["pct_of_capital"] == 20 and out["side"] == "short"


def test_streak_probability_matches_simulation():
    rng = np.random.default_rng(0)
    q, n, k = 0.55, 150, 8
    sims = rng.random((20000, n)) < q
    hit = 0
    for row in sims:
        run = best = 0
        for x in row:
            run = run + 1 if x else 0
            best = max(best, run)
        hit += best >= k
    assert prob_losing_streak(q, n, k) == pytest.approx(hit / 20000, abs=0.02)


def test_kelly_nonnegative():
    r = pd.Series(np.random.default_rng(1).normal(-0.001, 0.02, 500))
    assert kelly_from_returns(r)["recommended_leverage"] == 0.0


def _kill():
    return kill_conditions({"sharpe_per_period": 0.08, "max_drawdown_pct": -20.0})


def test_short_live_window_never_fires_decay():
    out = health_check(pd.Series([-0.001] * 30), _kill())
    assert "SHARPE_DECAY" not in out["alerts"] and out["notes"]


def test_decay_fires_on_real_decay():
    r = pd.Series(np.random.default_rng(2).normal(-0.002, 0.01, 200))
    assert "SHARPE_DECAY" in health_check(r, _kill())["alerts"]


def test_drawdown_halt():
    r = pd.Series([0.0] * 10 + [-0.05] * 8)
    out = health_check(r, _kill())
    assert "DRAWDOWN_EXCEEDED" in out["alerts"] and out["action"] == "HALT"
