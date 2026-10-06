import pandas as pd
import pytest

from btval.fills import calibrate, positions, shortfall, venue_gap
from btval.store import Store, assert_not_trading_db
from btval.venue import NotASimulator, assert_sim_url


def _rows(venue="binance"):
    base = dict(symbol="SOLUSDT", strategy_id=7, strategy_name="s", signal_bucket_ts="2026-10-05T08:00:00Z",
                opened_at="2026-10-05T08:05:00Z", closed_at="2026-10-05T12:00:00Z", funding_usd=0.0)
    return [
        # position 1: long, two partial closes, entry 10 bps worse than signal
        dict(base, id=1, position_id=1, direction="long", signal_price=100.0, entry_price=100.1,
             exit_price=101.0, notional_usd=500.0, pnl_usd=4.5, fee_usd=0.4),
        dict(base, id=2, position_id=1, direction="long", signal_price=100.0, entry_price=100.1,
             exit_price=102.0, notional_usd=500.0, pnl_usd=9.5, fee_usd=0.4),
        # position 2: short, entry 5 bps BELOW signal = adverse for a short
        dict(base, id=3, position_id=2, direction="short", signal_price=200.0, entry_price=199.9,
             exit_price=201.0, notional_usd=1000.0, pnl_usd=-5.5, fee_usd=0.8,
             signal_bucket_ts="2026-10-05T12:00:00Z"),
    ]


@pytest.fixture
def store(tmp_path):
    return Store(f"sqlite:///{tmp_path}/t.db")


@pytest.mark.parametrize("url", [
    "postgresql://pbservice:x@192.168.50.88:15442/pbTradeNet",
    "postgresql://u:p@192.168.50.88:15432/whatever",
    "postgresql://u:p@otherhost:5432/pbMasterData",
])
def test_store_refuses_trading_databases(url):
    with pytest.raises(RuntimeError):
        assert_not_trading_db(url)


def test_upsert_is_idempotent(store):
    assert store.upsert_fills(_rows(), "binance", "prod")["inserted"] == 3
    assert store.upsert_fills(_rows(), "binance", "prod")["inserted"] == 0
    assert store.max_source_row_id("binance", "prod") == 3


def test_positions_collapse_partial_closes(store):
    store.upsert_fills(_rows(), "binance", "prod")
    p = positions(store.load_fills()).set_index("position_id")
    assert len(p) == 2 and p.loc[1, "n_rows"] == 2
    assert p.loc[1, "entry_slip_bps"] == pytest.approx(10.0)
    assert p.loc[2, "entry_slip_bps"] == pytest.approx(5.0)   # short sold lower = adverse
    assert p.loc[1, "exit_vwap"] == pytest.approx(101.5)


def test_calibrate_recommends_measured_costs(store):
    store.upsert_fills(_rows(), "binance", "prod")
    c = calibrate(store.load_fills())
    assert c["n_positions"] == 2
    assert c["recommended_config"]["slippage_bps"] == pytest.approx(7.5)  # notional-weighted 10 & 5
    assert c["recommended_config"]["fee_bps"] == pytest.approx(4.0)       # 8 bps round trip / 2
    assert any("FILLED" in w for w in c["warnings"])


def test_shortfall_components_add_up(store):
    store.upsert_fills(_rows(), "binance", "prod")
    s = shortfall(store.load_fills())
    parts = s["shortfall_bps"]
    assert s["ideal_bps_per_position"] - s["net_bps_per_position"] == pytest.approx(sum(parts.values()), abs=1e-6)


def test_venue_gap_matches_on_signal(store):
    store.upsert_fills(_rows(), "binance", "prod")
    sim = _rows()
    for r in sim:
        r["entry_price"] = r["signal_price"]  # the fake fills at the signal price
    store.upsert_fills(sim[:2], "pbfinance", "preprod")
    g = venue_gap(store.load_fills(), "pbfinance", "binance")
    assert g["matched"] == 1 and g["only_binance"] == 1
    assert g["entry_slip_bps_diff_pbfinance_minus_binance"]["mean"] == pytest.approx(-10.0)


@pytest.mark.parametrize("url", ["https://fapi.binance.com", "https://fapi.binancefuture.com",
                                 "http://8.8.8.8:8976", "http://some-broker:8976",
                                 "http://pbfinance.example.com"])
def test_venue_refuses_non_simulators(url):
    with pytest.raises(NotASimulator):
        assert_sim_url(url)


def test_venue_accepts_allowlisted_internal():
    assert assert_sim_url("http://binance-simulator:8976/") == "http://binance-simulator:8976"
    with pytest.raises(NotASimulator):
        assert_sim_url("http://10.0.0.5:8976")            # internal but not allowlisted
    assert assert_sim_url("http://10.0.0.5:8976", allow="10.0.0.5")


def test_impossible_exit_is_excluded_and_reported(store):
    rows = _rows()
    rows.append(dict(rows[2], id=4, position_id=9, exit_price=1542.24, entry_price=95.6, signal_price=95.58,
                     symbol="SOLUSDT", direction="short"))
    store.upsert_fills(rows, "binance", "prod")
    c = calibrate(store.load_fills())
    assert c["n_positions"] == 2
    assert [r["source_row_id"] for r in c["excluded_rows"]] == [4]
    assert "exit_price" in c["excluded_rows"][0]["reason"]
    s = shortfall(store.load_fills())
    assert s["n_positions"] == 2 and len(s["excluded_rows"]) == 1


def test_pg_bar_loader_drops_forming_bar(monkeypatch):
    import types

    import pandas as pd

    from btval import data

    rows = [(pd.Timestamp("2026-10-04", tz="UTC"), 100.0), (pd.Timestamp("2026-10-05", tz="UTC"), 101.0),
            (pd.Timestamp("2026-10-06", tz="UTC"), 102.0)]

    class Cx:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, q, args=None):
            self.q = q
            return types.SimpleNamespace(fetchall=lambda: rows)
        def rollback(self): pass

    monkeypatch.setitem(__import__("sys").modules, "psycopg", types.SimpleNamespace(connect=lambda dsn: Cx()))
    s, notes = data.load_pg_bars("x", "master_data.cagg_ohlcv_1440m", 5, "open",
                                 now=pd.Timestamp("2026-10-06 06:00", tz="UTC"))
    assert list(s.values) == [100.0, 101.0]                # 10-06 bar closes 10-07: still forming
    assert s.index[-1] == pd.Timestamp("2026-10-06", tz="UTC")  # 10-05 bar stamped at its close
    assert any("still-forming" in n for n in notes)
    with pytest.raises(ValueError):
        data.load_pg_bars("x", "bad; drop table", 5, "open")


def test_performance_scoreboard(store):
    from btval.fills import performance
    for r in (rows := _rows()):
        r["size_usd"] = r["notional_usd"] / 5
    store.upsert_fills(rows, "binance", "prod")
    perf = performance(store.load_fills())
    t = perf["total"]
    assert t["trades"] == 2 and t["win_rate"] == 0.5
    assert t["pnl_usd"] == pytest.approx(8.5)
    assert t["roi_on_margin_pct"] == pytest.approx(8.5 / 400 * 100, abs=0.01)
    assert t["profit_factor"] == pytest.approx(14 / 5.5, rel=1e-3)


def test_reused_position_id_across_symbols_not_merged(store):
    rows = _rows()
    # same position_id as the SOL long, different strategy/symbol (seen live 2026-05-11)
    rows.append(dict(rows[0], id=10, position_id=1, symbol="ETHUSDT", strategy_name="other", session_id=99,
                     signal_price=2500.0, entry_price=2501.0, exit_price=2520.0))
    store.upsert_fills(rows, "binance", "prod")
    p = positions(store.load_fills())
    assert len(p) == 3
    assert p["exit_vwap"].max() < 3000 and calibrate(store.load_fills())["excluded_rows"] == []
