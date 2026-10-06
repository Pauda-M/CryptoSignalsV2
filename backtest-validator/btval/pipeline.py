"""Three hard gates. Skip one and you have built a fast way to lose money.

  Gate 1  CRITIC        no PRESENT finding on checks 1,2,3,4,5,8
  Gate 2  DEFLATED SR   full-sample best clears the multiple-testing bar
  Gate 3  WALK-FORWARD  out-of-sample folds hold up, sample has bull AND bear
"""
from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd
from scipy.stats import norm

from .config import Config, Gates
from .critic import PRESENT, critique, regime_report
from .engine import backtest
from .health import kill_conditions
from .metrics import metrics
from .sizing import kelly_from_returns
from .stats import deflated_sharpe, min_track_record_length
from .strategies import Strategy, get_strategy
from .walkforward import fit_on, walk_forward

GATE1_CHECKS = {1, 2, 3, 4, 5, 8}


def _gate1(findings) -> dict:
    blocking = [f for f in findings if f.id in GATE1_CHECKS and f.status == PRESENT]
    return {"status": "FAIL" if blocking else "PASS",
            "blocking": [f"{f.id}. {f.name}" for f in blocking],
            "unknown": [f"{f.id}. {f.name}" for f in findings if f.status == "UNKNOWN"]}


def worst_fold_floor(n_folds: int, fold_bars: float, periods_per_year: float, alpha: float = 0.05) -> float:
    """Annualized Sharpe below which a fold is worse than noise's worst fold."""
    se = np.sqrt(periods_per_year / max(fold_bars, 2))
    return float(-norm.ppf(1 - alpha / max(n_folds, 1)) * se)


def _gate3(wf: dict, findings, gates: Gates) -> dict:
    reasons = []
    if wf["positive_fold_ratio"] < gates.wf_min_positive_fold_ratio:
        reasons.append(f"positive folds {wf['positive_folds']}/{wf['n_folds']} < {gates.wf_min_positive_fold_ratio:.0%}")
    floor = gates.wf_min_worst_fold_sharpe
    if floor is None:
        fold_n = float(np.median([f["n_obs"] for f in wf["folds"].to_dict("records")]))
        floor = worst_fold_floor(wf["n_folds"], fold_n, wf["oos_metrics"]["periods_per_year"])
    wf["worst_fold_floor"] = round(floor, 3)
    if wf["worst_fold_sharpe"] < floor:
        reasons.append(f"worst fold Sharpe {wf['worst_fold_sharpe']} < {floor:.2f} (worse than noise's worst)")
    oos_sr = wf["oos_metrics"].get("sharpe", 0.0)
    if oos_sr <= gates.wf_min_oos_sharpe:
        reasons.append(f"stitched OOS Sharpe {oos_sr} <= {gates.wf_min_oos_sharpe}")
    regime = next(f for f in findings if f.id == 7)
    if regime.status == PRESENT:
        reasons.append("sample lacks bull and/or bear regime: walk-forward proves nothing about the missing one")
    return {"status": "FAIL" if reasons else "PASS", "reasons": reasons}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, pd.DataFrame):
        return _jsonable(o.to_dict("records"))
    if isinstance(o, pd.Series):
        return None
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def validate_strategy(prices: pd.Series, strategy: str | Strategy, cfg: Config | None = None,
                      gates: Gates | None = None, *, prior_trials: int = 0,
                      train_bars: int = 365, test_bars: int = 90, anchored: bool = False,
                      universe: list[dict] | None = None, bar_label: str | None = "close",
                      trial_log: list[float] | None = None) -> dict:
    """Full validation of a registry strategy.

    prior_trials: variations you ran BEFORE coming here (other strategies,
        other grids, other timeframes on this data). Every one counts.
    trial_log: per-period Sharpes of those prior trials, if you kept them.
    """
    cfg = cfg or Config()
    gates = gates or Gates()
    strat = get_strategy(strategy) if isinstance(strategy, str) else strategy

    # In-sample: what you would have traded if you just picked the best curve.
    best, trials = fit_on(prices, strat, cfg)
    sig = strat.signal(prices, **best)
    is_bt = backtest(prices, sig, cfg)
    is_m = metrics(is_bt["net"].iloc[strat.warmup:], cfg)

    wf = walk_forward(prices, strat, cfg, train_bars=train_bars, test_bars=test_bars, anchored=anchored)

    findings = critique(
        prices, sig, cfg, gates,
        signal_fn=partial(strat.signal, **best),
        source=strat.source(),
        universe=universe, bar_label=bar_label,
        n_params=len(strat.grid), params_fit_out_of_sample=True, warmup=strat.warmup,
    )
    findings[5].evidence.append(f"grid size {len(trials)}; in-sample best {best}")
    g1 = _gate1(findings)

    n_trials = prior_trials + len(trials)
    all_srs = [t["sharpe_per_period"] for t in trials] + list(trial_log or [])
    g2_dsr = deflated_sharpe(is_m["sharpe_per_period"], n_trials, is_m["n_obs"],
                             is_m["skew"], is_m["kurtosis"], trial_sharpes=all_srs,
                             threshold=gates.dsr_min)
    g2 = {"status": "PASS" if g2_dsr["verdict"] == "PASS" else "FAIL", **g2_dsr}

    oos_m = wf["oos_metrics"]
    oos_dsr = deflated_sharpe(oos_m["sharpe_per_period"], prior_trials + 1, oos_m["n_obs"],
                              oos_m["skew"], oos_m["kurtosis"], threshold=gates.dsr_min)
    g3 = _gate3(wf, findings, gates)

    verdict = "DEPLOYABLE" if all(g["status"] == "PASS" for g in (g1, g2, g3)) else "REJECT"
    report = {
        "verdict": verdict,
        "strategy": {"name": strat.name, "mechanism": strat.mechanism or "NONE STATED — a pattern, not an edge",
                     "grid": strat.grid, "in_sample_best": best},
        "config": cfg.to_dict(),
        "gate_thresholds": gates.to_dict(),
        "gates": {"1_critic": g1, "2_deflated_sharpe": g2, "3_walk_forward": g3},
        "critic": [f.to_dict() for f in findings],
        "in_sample": {"metrics": is_m, "trials": trials,
                      "note": "In-sample numbers are the selection-biased ones. Do not quote them."},
        "walk_forward": {k: v for k, v in wf.items() if k not in ("oos_net", "oos_backtest")},
        "oos_deflated_sharpe": oos_dsr,
        "oos_regimes": regime_report(prices, wf["oos_net"], cfg),
        "min_track_record_bars": min_track_record_length(
            oos_m["sharpe_per_period"], oos_m["skew"], oos_m["kurtosis"]),
        "sizing": kelly_from_returns(wf["oos_net"]),
        # Kill conditions come from OUT-OF-SAMPLE stats, fixed now while objective.
        "kill_conditions": kill_conditions(oos_m) if verdict == "DEPLOYABLE" else None,
    }
    return _jsonable(report)


def validate_signal(prices: pd.Series, signal: pd.Series, cfg: Config | None = None,
                    gates: Gates | None = None, *, n_trials: int, trial_log: list[float] | None = None,
                    holdout_start: str | None = None, fold_bars: int = 90,
                    source: str | None = None, backtest_source: str | None = None,
                    n_params: int | None = None, universe: list[dict] | None = None,
                    bar_label: str | None = None) -> dict:
    """Validate a precomputed signal.

    Weaker than validate_strategy by construction: there is no signal
    function to probe, and no refit. Gate 3 needs ``holdout_start`` — the
    date after which the signal's rules were frozen and never looked at.
    Without it there is no out-of-sample data and gate 3 fails.
    """
    cfg = cfg or Config()
    gates = gates or Gates()
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1. If you think it's 1, count again.")
    signal = signal.reindex(prices.index)
    if signal.isna().any():
        raise ValueError(f"signal missing {int(signal.isna().sum())} bars of the price index")

    findings = critique(prices, signal, cfg, gates, source=source, user_backtest_source=backtest_source,
                        universe=universe, bar_label=bar_label, n_params=n_params,
                        params_fit_out_of_sample=holdout_start is not None)
    g1 = _gate1(findings)

    bt = backtest(prices, signal, cfg)
    full = bt["net"]
    is_net = full[full.index < pd.Timestamp(holdout_start, tz=full.index.tz)] if holdout_start else full
    is_m = metrics(is_net, cfg)
    dsr = deflated_sharpe(is_m["sharpe_per_period"], n_trials, is_m["n_obs"], is_m["skew"],
                          is_m["kurtosis"], trial_sharpes=trial_log, threshold=gates.dsr_min)
    g2 = {"status": "PASS" if dsr["verdict"] == "PASS" else "FAIL", **dsr}

    if holdout_start is None:
        g3 = {"status": "FAIL", "reasons": ["no holdout_start: every bar was visible when the rules were written"]}
        wf_out = None
    else:
        oos = full[full.index >= pd.Timestamp(holdout_start, tz=full.index.tz)]
        folds = []
        for i in range(0, len(oos), fold_bars):
            seg = oos.iloc[i:i + fold_bars]
            if len(seg) < max(10, fold_bars // 3):
                continue
            m = metrics(seg, cfg)
            folds.append({"test_start": seg.index[0], "test_end": seg.index[-1],
                          "sharpe": m["sharpe"], "return_pct": m["total_return_pct"], "n_obs": m["n_obs"]})
        df = pd.DataFrame(folds)
        if df.empty:
            g3 = {"status": "FAIL", "reasons": ["holdout too short for a single fold"]}
            wf_out = None
        else:
            wf = {"folds": df, "n_folds": len(df), "positive_folds": int((df.sharpe > 0).sum()),
                  "positive_fold_ratio": round(float((df.sharpe > 0).mean()), 3),
                  "worst_fold_sharpe": round(float(df.sharpe.min()), 3),
                  "oos_metrics": metrics(oos, cfg)}
            g3 = _gate3(wf, findings, gates)
            wf_out = wf

    verdict = "DEPLOYABLE" if all(g["status"] == "PASS" for g in (g1, g2, g3)) else "REJECT"
    oos_m = wf_out["oos_metrics"] if wf_out else None
    return _jsonable({
        "verdict": verdict,
        "config": cfg.to_dict(),
        "gate_thresholds": gates.to_dict(),
        "gates": {"1_critic": g1, "2_deflated_sharpe": g2, "3_walk_forward": g3},
        "critic": [f.to_dict() for f in findings],
        "in_sample": is_m,
        "holdout": wf_out,
        "kill_conditions": kill_conditions(oos_m) if verdict == "DEPLOYABLE" and oos_m else None,
    })
