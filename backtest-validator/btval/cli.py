"""btval CLI.

  btval validate --csv BTCUSDT_1d.csv --bar-label open --strategy tsmom --prior-trials 12
  btval demo
  btval serve --port 8790
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import Config, Gates
from .data import load_csv, normalize_bars, synthetic_prices
from .pipeline import validate_strategy


def _print(rep: dict, as_json: bool) -> None:
    if as_json:
        json.dump(rep, sys.stdout, indent=2, default=str)
        print()
        return
    print(f"VERDICT: {rep['verdict']}")
    for name, g in rep["gates"].items():
        extra = g.get("blocking") or g.get("reasons") or ""
        if "deflated_sharpe" in g:
            extra = f"DSR={g['deflated_sharpe']} (trials={g['n_trials']}, noise bar SR/bar={g['expected_max_sr_per_period']:.4f})"
        print(f"  gate {name:<20} {g['status']:<5} {extra}")
    print("CRITIC")
    for f in rep["critic"]:
        print(f"  {f['id']}. [{f['status']}] {f['name']}")
        for e in f["evidence"]:
            print(f"       {e}")
        if f["detail"]:
            print(f"       -> {f['detail']}")
    wf = rep.get("walk_forward")
    if wf:
        print(f"WALK-FORWARD positive {wf['positive_folds']}/{wf['n_folds']}, worst {wf['worst_fold_sharpe']}, "
              f"median {wf['median_fold_sharpe']}, OOS Sharpe {wf['oos_metrics']['sharpe']}, param changes {wf['param_changes']}")
    if rep.get("kill_conditions"):
        print("KILL CONDITIONS (fixed now):", json.dumps(rep["kill_conditions"]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="btval")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate a registry strategy on a CSV")
    v.add_argument("--csv", required=True)
    v.add_argument("--bar-label", required=True, choices=["open", "close"])
    v.add_argument("--strategy", required=True)
    v.add_argument("--prior-trials", type=int, required=True,
                   help="variations tried before this run (required: no default lets you forget)")
    v.add_argument("--train-bars", type=int, default=365)
    v.add_argument("--test-bars", type=int, default=90)
    v.add_argument("--fee-bps", type=float, default=5.0)
    v.add_argument("--slippage-bps", type=float, default=3.0)
    v.add_argument("--json", action="store_true")

    d = sub.add_parser("demo", help="run on a synthetic no-edge random walk")
    d.add_argument("--json", action="store_true")

    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8790)

    a = ap.parse_args(argv)
    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("btval.api:app", host=a.host, port=a.port)
        return 0
    if a.cmd == "demo":
        rep = validate_strategy(synthetic_prices(regime_drift=False), "tsmom", prior_trials=0)
        _print(rep, a.json)
        return 0
    prices, notes = normalize_bars(load_csv(a.csv), a.bar_label)
    for n in notes:
        print("note:", n, file=sys.stderr)
    cfg = Config(fee_bps=a.fee_bps, slippage_bps=a.slippage_bps)
    rep = validate_strategy(prices, a.strategy, cfg, Gates(), prior_trials=a.prior_trials,
                            train_bars=a.train_bars, test_bars=a.test_bars, bar_label="close")
    _print(rep, a.json)
    return 0 if rep["verdict"] == "DEPLOYABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
