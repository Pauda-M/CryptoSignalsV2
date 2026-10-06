from fastapi.testclient import TestClient

from btval.api import app
from btval.data import synthetic_prices

c = TestClient(app)


def _bars(n=900):
    p = synthetic_prices(n=n, seed=5, regime_drift=False)
    return [{"timestamp": int(t.timestamp() * 1000), "close": float(v)} for t, v in p.items()]


def test_health_and_strategies():
    assert c.get("/health").json()["status"] == "ok"
    assert {s["name"] for s in c.get("/strategies").json()} >= {"sma_cross", "tsmom"}


def test_validate_strategy_open_bars_restamped():
    r = c.post("/validate/strategy", json={"bars": _bars(), "bar_label": "open", "strategy": "tsmom",
                                           "prior_trials": 3, "train_bars": 300, "test_bars": 90})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] in ("REJECT", "DEPLOYABLE")
    assert body["data_notes"] and "re-stamped" in body["data_notes"][0]


def test_bar_label_required():
    r = c.post("/validate/strategy", json={"bars": _bars(), "strategy": "tsmom"})
    assert r.status_code == 422


def test_validate_signal_length_mismatch():
    r = c.post("/validate/signal", json={"bars": _bars(100), "bar_label": "close",
                                         "signal": [1.0] * 99, "n_trials": 1})
    assert r.status_code == 422


def test_validate_signal_with_holdout():
    bars = _bars(800)
    r = c.post("/validate/signal", json={"bars": bars, "bar_label": "close", "signal": [1.0] * 800,
                                         "n_trials": 4, "holdout_start": "2021-06-01",
                                         "source": "sig = prices.rolling(20, center=True).mean()"})
    assert r.status_code == 200, r.text
    f3 = next(f for f in r.json()["critic"] if f["id"] == 3)
    assert f3["status"] == "PRESENT"


def test_dsr_and_size_and_monitor():
    d = c.post("/stats/deflated-sharpe", json={"sharpe_per_period": 0.05, "n_trials": 100, "n_obs": 1000}).json()
    assert d["verdict"] in ("PASS", "REJECT")
    s = c.post("/size", json={"capital": 1e4, "entry": 100, "stop": 95, "win_rate": 0.45,
                              "trades_per_year": 150}).json()
    assert s["position"]["units"] > 0 and s["streaks"]["rows"]
    m = c.post("/monitor", json={"live_returns": [0.001] * 100, "kill_conditions": {"expected_sr_per_period": 0.05}})
    assert m.status_code == 422


def test_signal_moves_with_restamped_duplicated_bars():
    bars = _bars(300)
    bars.insert(10, dict(bars[10]))  # duplicate bar
    r = c.post("/validate/signal", json={"bars": bars, "bar_label": "open", "signal": [1.0] * 301,
                                         "n_trials": 1})
    assert r.status_code == 200, r.text


def test_ingest_calibrate_paper_and_dashboard(monkeypatch):
    import numpy as np

    from btval import api
    from btval.venue import SimVenue

    from .fake_pbfinance import FakePbFinance

    rows = [dict(id=i, position_id=i, symbol="BTCUSDT", direction="long", signal_price=100.0,
                 entry_price=100.0 + 0.01 * i, exit_price=101.0, notional_usd=1000.0, pnl_usd=9.0,
                 fee_usd=0.8, api_key_ref="SECRET", signal_bucket_ts="2026-10-05T08:00:00Z",
                 opened_at="2026-10-05T08:01:00Z", closed_at="2026-10-05T10:00:00Z") for i in range(1, 6)]
    r = c.post("/ingest/trades", json={"venue": "binance", "source_db": "t-prod", "rows": rows})
    assert r.json()["inserted"] == 5
    cal = c.post("/fills/calibrate", json={"venue": "binance"}).json()
    assert cal["calibration_id"] and cal["recommended_config"]["fee_bps"] == 4.0

    run = c.post("/validate/strategy", json={"bars": _bars(), "bar_label": "close", "strategy": "sma_cross",
                                              "prior_trials": 1, "train_bars": 300, "test_bars": 90,
                                              "calibration_id": cal["calibration_id"]}).json()
    assert run["run_id"] and run["config"]["fee_bps"] == 4.0

    monkeypatch.setenv("BTVAL_SIM_URL", "http://binance-simulator:8976")
    r = c.post("/paper/sessions", json={"strategy": "sma_cross", "symbol": "BTCUSDT",
                                        "validation_run_id": run["run_id"], "calibration_id": cal["calibration_id"]})
    if run["verdict"] != "DEPLOYABLE":
        assert r.status_code == 422
        r = c.post("/paper/sessions", json={"strategy": "sma_cross", "symbol": "BTCUSDT", "params": {"fast": 10, "slow": 50},
                                            "allow_unvalidated": True, "calibration_id": cal["calibration_id"]})
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]

    fake = FakePbFinance(list(100 * np.exp(np.linspace(0, .4, 260))))
    api.app.dependency_overrides[api.get_venue] = lambda: SimVenue(
        "http://binance-simulator:8976", "k", "s", client=fake.client(), clock=fake.clock)
    try:
        t = c.post(f"/paper/sessions/{sid}/tick").json()
        assert t["order"]["status"] == "filled"
    finally:
        api.app.dependency_overrides.clear()
    sessions = c.get("/paper/sessions").json()
    s = next(x for x in sessions if x["id"] == sid)
    assert s["unvalidated"] is (run["verdict"] != "DEPLOYABLE") and s["equity"] is not None
    assert len(c.get(f"/paper/sessions/{sid}/equity").json()) == 1
    assert c.get(f"/paper/sessions/{sid}/orders").json()[0]["status"] == "filled"
    assert c.get("/calibrations").json()
    html = c.get("/")
    assert html.status_code == 200 and "paper monitor" in html.text


def test_paper_refuses_live_venue(monkeypatch):
    monkeypatch.setenv("BTVAL_SIM_URL", "https://fapi.binance.com")
    r = c.post("/paper/sessions", json={"strategy": "sma_cross", "symbol": "BTCUSDT", "allow_unvalidated": True,
                                        "fee_bps": 4, "slippage_bps": 2})
    assert r.status_code == 403
