import numpy as np
import pytest
from sqlalchemy import select

from btval.paper import create_session, report, tick
from btval.store import Store, paper_orders
from btval.venue import SimVenue

from .fake_pbfinance import FakePbFinance

KILL = {"expected_sr_per_period": 0.05, "backtest_max_dd_pct": -10.0, "max_dd_pct_limit": -15.0,
        "decay_fraction": 0.5, "min_window": 90, "alpha": 0.05}


@pytest.fixture
def store(tmp_path):
    return Store(f"sqlite:///{tmp_path}/p.db")


def _deployable_run(store, kill=KILL):
    return store.save_run("strategy", "sma_cross", {"verdict": "DEPLOYABLE", "kill_conditions": kill})


def _venue(fake):
    return SimVenue("http://binance-simulator:8976", "k", "s", client=fake.client(), clock=fake.clock)


def _uptrend(n=260):
    return list(100 * np.exp(np.linspace(0, 0.5, n)))


def _session(store, run_id=None, **kw):
    args = dict(strategy="sma_cross", params={"fast": 10, "slow": 50}, symbol="BTCUSDT", interval="1d",
                venue_url="http://binance-simulator:8976",
                cost_model={"mode": "fixed", "slippage_bps": 5.0, "fee_bps": 4.0},
                validation_run_id=run_id if run_id is not None else _deployable_run(store))
    args.update(kw)
    return create_session(store, **args)


def test_refuses_rejected_or_missing_validation(store):
    rej = store.save_run("strategy", "x", {"verdict": "REJECT", "kill_conditions": None})
    with pytest.raises(ValueError):
        _session(store, run_id=rej)
    with pytest.raises(ValueError):
        create_session(store, strategy="sma_cross", params={}, symbol="BTCUSDT", interval="1d",
                       venue_url="http://binance-simulator:8976", cost_model={"mode": "none"})


def test_refuses_live_url_at_session_creation(store):
    from btval.venue import NotASimulator
    with pytest.raises(NotASimulator):
        _session(store, venue_url="https://fapi.binance.com")


def test_tick_places_one_order_per_bar_with_realistic_fill(store):
    fake = FakePbFinance(_uptrend())
    sid = _session(store)
    out = tick(store, _venue(fake), sid)
    o = out["order"]
    assert o["status"] == "filled" and len(fake.orders) == 1
    # decision on the last CLOSED bar, not the forming one
    assert o["decision_price"] == pytest.approx(fake.closes[-2])
    assert o["venue_drift_bps"] == pytest.approx(2.0, abs=0.01)
    assert o["realistic_price"] == pytest.approx(o["venue_avg_price"] * (1 + 5 / 1e4))
    assert out["reconcile"]["diverged"] is False

    again = tick(store, _venue(fake), sid)
    assert again["order"]["status"] == "already_decided"
    assert len(fake.orders) == 1


def test_halt_flattens_and_stops(store):
    fake = FakePbFinance(_uptrend())
    kill = dict(KILL, max_dd_pct_limit=-3.0)   # 10% drop on ~50% exposure breaches this
    sid = _session(store, run_id=_deployable_run(store, kill))
    tick(store, _venue(fake), sid)
    fake.closes[-1] = fake.closes[-2] * 0.9               # forming bar closes 10% lower
    fake.advance(fake.closes[-1])
    out = tick(store, _venue(fake), sid)
    assert out["health"]["action"] == "HALT"
    assert out["halt_order"]["status"] == "filled"
    assert fake.position == pytest.approx(0.0, abs=1e-9)
    assert tick(store, _venue(fake), sid)["status"] == "halted"


def test_report(store):
    fake = FakePbFinance(_uptrend())
    sid = _session(store)
    tick(store, _venue(fake), sid)
    r = report(store, sid)
    assert r["orders"] == {"filled": 1}
    assert r["venue_drift_bps"]["mean"] == pytest.approx(2.0, abs=0.01)
    assert r["fees_usd"] > 0


def test_costs_alone_can_halt(store):
    fake = FakePbFinance(_uptrend())
    sid = _session(store, run_id=_deployable_run(store, dict(KILL, max_dd_pct_limit=-0.0001)))
    out = tick(store, _venue(fake), sid)
    assert out["health"]["action"] == "HALT" and fake.position == pytest.approx(0.0, abs=1e-9)


def test_equity_snapshots_and_listing(store):
    from btval.paper import equity_series, list_sessions
    fake = FakePbFinance(_uptrend())
    sid = _session(store)
    tick(store, _venue(fake), sid)
    fake.advance(fake.closes[-1] * 1.01)
    tick(store, _venue(fake), sid)
    eq = equity_series(store, sid)
    assert len(eq) == 2 and eq[0]["drawdown_pct"] <= 0
    s = next(x for x in list_sessions(store) if x["id"] == sid)
    assert s["status"] == "active" and s["equity"] == pytest.approx(eq[-1]["equity"])


def test_run_must_match_strategy(store):
    rid = _deployable_run(store)  # subject sma_cross
    with pytest.raises(ValueError, match="validated"):
        _session(store, run_id=rid, strategy="tsmom", params={"lookback": 20})


def test_rebalance_band_skips_equity_drift(store):
    fake = FakePbFinance(_uptrend())
    sid = _session(store, max_order_notional=1e9)
    tick(store, _venue(fake), sid)
    fake.advance(fake.closes[-1] * 1.01)   # equity drifts 1%, signal unchanged
    out = tick(store, _venue(fake), sid)
    assert out["order"]["status"] == "no_trade" and "band" in out["order"]["note"]
    assert len(fake.orders) == 1


def test_trade_stats_round_trip():
    import pandas as pd

    from btval.paper import trade_stats
    led = pd.DataFrame([
        dict(id=1, bar_ts=1, status="filled", venue_executed_qty=1.0, realistic_price=100.0, fee_usd=0.1),
        dict(id=2, bar_ts=2, status="filled", venue_executed_qty=-1.0, realistic_price=110.0, fee_usd=0.1),
        dict(id=3, bar_ts=3, status="filled", venue_executed_qty=-1.0, realistic_price=110.0, fee_usd=0.1),
        dict(id=4, bar_ts=4, status="filled", venue_executed_qty=1.0, realistic_price=115.0, fee_usd=0.1),
        dict(id=5, bar_ts=5, status="filled", venue_executed_qty=2.0, realistic_price=100.0, fee_usd=0.1),
    ])
    st = trade_stats({"initial_capital": 1000.0}, led, mark=105.0)
    assert st["round_trips"] == 2 and st["win_rate"] == 0.5
    assert st["realized_pnl_usd"] == pytest.approx(10 - 5 - 0.5)
    assert st["unrealized_pnl_usd"] == pytest.approx(10.0)
    assert st["roi_pct"] == pytest.approx((4.5 + 10) / 1000 * 100)
