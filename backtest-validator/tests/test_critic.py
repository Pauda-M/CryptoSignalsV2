import inspect

import pandas as pd

from btval.config import Config, Gates
from btval.critic import PRESENT, critique, perturbation_probe, scan_repainting
from btval.pipeline import validate_signal, validate_strategy
from btval.strategies import Strategy

from . import cheaters


def _by_id(fs):
    return {f.id: f for f in fs}


def test_probe_catches_negative_shift(rw):
    assert perturbation_probe(rw, cheaters.peek)["failures"]


def test_probe_catches_centered_window(rw):
    assert perturbation_probe(rw, cheaters.centered)["failures"]


def test_probe_catches_global_normalization(rw):
    # no regex marks this as a hard leak; the probe proves it
    assert perturbation_probe(rw, cheaters.global_zscore)["failures"]


def test_probe_passes_causal_signal(rw):
    assert not perturbation_probe(rw, cheaters.honest, warmup=50)["failures"]


def test_static_scan_quotes_lines():
    hits = scan_repainting(inspect.getsource(cheaters))
    quoted = " ".join(q for q, _ in hits)
    assert "shift(-1)" in quoted and "center=True" in quoted and "prices.mean()" in quoted
    assert all(q.startswith("L") for q, _ in hits)


def test_cheater_strategy_rejected_at_gate1(rw):
    s = Strategy("peek", cheaters.peek, mechanism="none")
    rep = validate_strategy(rw, s, train_bars=365, test_bars=90)
    assert rep["verdict"] == "REJECT"
    assert rep["gates"]["1_critic"]["status"] == "FAIL"
    f = {x["id"]: x for x in rep["critic"]}
    assert f[1]["status"] == PRESENT and f[3]["status"] == PRESENT


def test_open_stamped_bars_flagged(rw):
    sig = cheaters.honest(rw)
    f = _by_id(critique(rw, sig, Config(), Gates(), bar_label="open"))
    assert f[8].status == PRESENT


def test_tz_mismatch_flagged(rw):
    other = rw.tz_convert("Europe/Helsinki")
    f = _by_id(critique(rw, cheaters.honest(rw), Config(), Gates(), bar_label="close",
                        extra_series={"funding": other}))
    assert f[8].status == PRESENT


def test_survivorship_universe_without_delistings(rw):
    uni = [{"symbol": s} for s in ("BTC", "ETH", "SOL")]
    f = _by_id(critique(rw, cheaters.honest(rw), Config(), Gates(), universe=uni))
    assert f[2].status == PRESENT


def test_user_backtest_without_shift_flagged(rw):
    src = "position = signal\npnl = position * returns\n"
    f = _by_id(critique(rw, cheaters.honest(rw), Config(), Gates(), user_backtest_source=src))
    assert f[1].status == PRESENT
    assert "L1: position = signal" in " ".join(f[1].evidence)


def test_zero_costs_fail_gate1(rw):
    sig = cheaters.honest(rw)
    rep = validate_signal(rw, sig, Config(slippage_bps=0), n_trials=1, bar_label="close")
    assert rep["gates"]["1_critic"]["status"] == "FAIL"


def test_signal_without_holdout_fails_gate3(rw):
    rep = validate_signal(rw, cheaters.honest(rw), n_trials=1, bar_label="close")
    assert rep["gates"]["3_walk_forward"]["status"] == "FAIL"
    assert rep["verdict"] == "REJECT"
