"""btval CLI.

  btval validate --csv BTCUSDT_1d.csv --bar-label open --strategy tsmom --prior-trials 12
  btval demo
  btval serve --port 8790
"""
from __future__ import annotations

import argparse
import json
import os
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
    src = v.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--pg-table", help="schema.table of OHLCV bars, e.g. master_data.cagg_ohlcv_1440m")
    v.add_argument("--pg-dsn", default=os.environ.get("BTVAL_BARS_DSN"), help="default $BTVAL_BARS_DSN; read-only use")
    v.add_argument("--pair-id", type=int)
    v.add_argument("--since")
    v.add_argument("--calibration-id", type=int, help="use measured fee/slippage from a stored calibration")
    v.add_argument("--save", action="store_true", help="store the run in btval's DB (shows on the dashboard)")
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

    ca = sub.add_parser("calibrate", help="measured fee/slippage from stored fills")
    ca.add_argument("--venue")
    ca.add_argument("--strategy-id", type=int)
    ca.add_argument("--since")

    pt = sub.add_parser("paper-tick", help="one bar of paper trading on pbFinance")
    pt.add_argument("--session", type=int, required=True)

    pl = sub.add_parser("paper-loop", help="tick every active paper session forever (idempotent per bar)")
    pl.add_argument("--every", type=int, default=60, help="seconds between passes")

    mr = sub.add_parser("bars-mirror", help="copy live 1m bars from pbMasterData into pbFinance's own DB")
    mr.add_argument("--source-dsn", default=os.environ.get("BTVAL_BARS_DSN"))
    mr.add_argument("--target-dsn", default=os.environ.get("PBFINANCE_DB_DSN"))
    mr.add_argument("--every", type=int, default=10)
    mr.add_argument("--backfill-days", type=float, default=3.0)
    mr.add_argument("--once", action="store_true")

    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8790)

    a = ap.parse_args(argv)
    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("btval.api:app", host=a.host, port=a.port)
        return 0
    if a.cmd == "calibrate":
        from .fills import calibrate
        from .store import Store
        st = Store()
        res = calibrate(st.load_fills(a.venue, a.strategy_id, since=a.since))
        if "error" not in res:
            res["calibration_id"] = st.save_calibration(
                {"venue": a.venue, "strategy_id": a.strategy_id, "since": a.since}, res)
        res.pop("empirical_slippage_bps", None)
        print(json.dumps(res, default=str, indent=2))
        return 0
    if a.cmd == "paper-tick":
        from .paper import tick
        from .store import Store
        from .venue import SimVenue
        v = SimVenue(os.environ["BTVAL_SIM_URL"], os.environ.get("BTVAL_SIM_API_KEY", ""),
                     os.environ.get("BTVAL_SIM_API_SECRET", ""))
        print(json.dumps(tick(Store(), v, a.session), default=str, indent=2))
        return 0
    if a.cmd == "bars-mirror":
        from .mirror import run
        if not (a.source_dsn and a.target_dsn):
            ap.error("--source-dsn/$BTVAL_BARS_DSN and --target-dsn/$PBFINANCE_DB_DSN required")
        run(a.source_dsn, a.target_dsn, a.every, a.backfill_days, once=a.once)
        return 0
    if a.cmd == "paper-loop":
        import time

        from .paper import list_sessions, tick
        from .store import Store
        from .venue import SimVenue
        st = Store()
        v = SimVenue(os.environ["BTVAL_SIM_URL"], os.environ.get("BTVAL_SIM_API_KEY", ""),
                     os.environ.get("BTVAL_SIM_API_SECRET", ""))
        while True:
            for sess in list_sessions(st):
                if sess["status"] != "active":
                    continue
                try:
                    out = tick(st, v, sess["id"])
                    o = out.get("order", {})
                    if o.get("status") != "already_decided":
                        print(json.dumps({"session": sess["id"], "bar": out.get("bar_ts"), "order": o.get("status"),
                                          "equity": out.get("equity"),
                                          "action": (out.get("health") or {}).get("action")}, default=str), flush=True)
                except Exception as e:  # noqa: BLE001 -- one session failing must not stop the others
                    print(json.dumps({"session": sess["id"], "error": f"{type(e).__name__}: {e}"}), flush=True)
            time.sleep(a.every)
    if a.cmd == "demo":
        rep = validate_strategy(synthetic_prices(regime_drift=False), "tsmom", prior_trials=0)
        _print(rep, a.json)
        return 0
    if a.csv:
        prices, notes = normalize_bars(load_csv(a.csv), a.bar_label)
    else:
        if not (a.pg_dsn and a.pair_id is not None):
            ap.error("--pg-table needs --pg-dsn (or $BTVAL_BARS_DSN) and --pair-id")
        from .data import load_pg_bars
        prices, notes = load_pg_bars(a.pg_dsn, a.pg_table, a.pair_id, a.bar_label, a.since)
    for n in notes:
        print("note:", n, file=sys.stderr)
    cfg = Config(fee_bps=a.fee_bps, slippage_bps=a.slippage_bps)
    store = None
    if a.calibration_id is not None or a.save:
        from .store import Store
        store = Store()
    if a.calibration_id is not None:
        cal = store.get_calibration(a.calibration_id)
        if cal is None:
            ap.error(f"calibration {a.calibration_id} not found")
        rec = cal["result"]["recommended_config"]
        cfg.fee_bps, cfg.slippage_bps = float(rec["fee_bps"]), float(rec["slippage_bps"])
    rep = validate_strategy(prices, a.strategy, cfg, Gates(), prior_trials=a.prior_trials,
                            train_bars=a.train_bars, test_bars=a.test_bars, bar_label="close")
    rep["data_notes"] = notes
    rep["data"] = {"source": a.csv or f"{a.pg_table}#pair_id={a.pair_id}", "bars": len(prices),
                   "first": str(prices.index[0]), "last": str(prices.index[-1])}
    if a.calibration_id is not None:
        rep["calibration"] = {"calibration_id": a.calibration_id, "fee_bps": cfg.fee_bps,
                              "slippage_bps": cfg.slippage_bps}
    if a.save:
        rep["run_id"] = store.save_run("strategy", a.strategy, rep, a.prior_trials)
        print(f"saved run #{rep['run_id']}", file=sys.stderr)
    _print(rep, a.json)
    return 0 if rep["verdict"] == "DEPLOYABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
