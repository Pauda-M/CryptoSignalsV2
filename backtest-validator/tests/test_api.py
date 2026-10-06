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
