import pytest

from btval.data import synthetic_prices
from btval.pipeline import validate_strategy, worst_fold_floor
from btval.strategies import get_strategy
from btval.walkforward import walk_forward


def test_warmup_history_used_in_folds(rw):
    s = get_strategy("sma_cross")
    wf = walk_forward(rw, s, train_bars=400, test_bars=60)
    first_test = wf["folds"].iloc[0]["test_start"]
    # a slow MA computed on the 60-bar test slice alone would be flat for the whole fold
    assert wf["oos_backtest"].loc[first_test:].iloc[:60]["position"].abs().sum() > 0


def test_short_folds_do_not_crash(rw):
    wf = walk_forward(rw, get_strategy("tsmom"), train_bars=200, test_bars=20)
    assert wf["n_folds"] > 10 and wf["folds"]["low_sample"].all()


def test_worst_fold_floor_scales_with_fold_count():
    assert worst_fold_floor(50, 90, 365) < worst_fold_floor(5, 90, 365) < 0


def test_random_walk_rejected(rw):
    rep = validate_strategy(rw, "tsmom", prior_trials=0)
    assert rep["verdict"] == "REJECT"
    assert rep["kill_conditions"] is None


@pytest.mark.parametrize("seed", [1, 2])
def test_planted_edge_deployable(seed, ar1_strategy):
    p = synthetic_prices(n=5000, seed=seed, phi=0.1, regime_drift=False)
    rep = validate_strategy(p, ar1_strategy, prior_trials=5)
    assert rep["verdict"] == "DEPLOYABLE", rep["gates"]
    k = rep["kill_conditions"]
    assert k and k["max_dd_pct_limit"] < k["backtest_max_dd_pct"] < 0


def test_same_edge_same_strategy_more_trials_rejected(ar1_strategy):
    p = synthetic_prices(n=1825, seed=1, phi=0.1, regime_drift=False)
    rep = validate_strategy(p, ar1_strategy, prior_trials=5000)
    assert rep["gates"]["2_deflated_sharpe"]["status"] == "FAIL"
