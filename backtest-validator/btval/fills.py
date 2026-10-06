"""Execution reality, measured from fills instead of assumed.

Fill rows may be partial closes (one row per TP rung / stop). Entry-side
quantities are per POSITION; fee/funding/pnl are summed over its rows.
Sign convention: positive bps = adverse to you.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _sign(direction: pd.Series) -> pd.Series:
    return np.where(direction.str.lower().str.startswith("l"), 1.0, -1.0)


# A price more than this factor away from the position's own entry is not a fill.
SUSPECT_FACTOR = 3.0


def suspect_rows(df: pd.DataFrame, factor: float = SUSPECT_FACTOR) -> pd.DataFrame:
    """Rows whose exit or signal price is impossible relative to their entry."""
    if df.empty:
        return df
    e = df["entry_price"].astype(float)
    bad = pd.Series(False, index=df.index)
    reasons = pd.Series("", index=df.index)
    for col in ("exit_price", "signal_price"):
        if col in df:
            r = df[col].astype(float) / e
            m = r.notna() & ((r > factor) | (r < 1 / factor) | (df[col] <= 0))
            bad |= m
            reasons = reasons.where(~m, reasons + f"{col} {factor:g}x off entry; ")
    out = df.loc[bad, ["source_row_id", "venue", "source_db", "position_id", "strategy_name", "symbol",
                       "entry_price", "exit_price", "signal_price", "closed_at"]].copy()
    out["reason"] = reasons[bad].str.strip("; ")
    return out


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Drop whole positions that contain a suspect row; return what was dropped."""
    bad = suspect_rows(df)
    if bad.empty:
        return df, []
    keys = set(zip(bad["venue"], bad["source_db"], bad["position_id"], bad["symbol"]))
    keep = ~pd.Series([k in keys for k in zip(df["venue"], df["source_db"], df["position_id"], df["symbol"])],
                      index=df.index)
    rows = bad.assign(closed_at=bad["closed_at"].astype(str)).to_dict("records")
    return df[keep], rows


# position_id alone is not guaranteed unique across sessions/symbols, so a
# position is keyed by all of these.
POSITION_KEY = ["venue", "source_db", "session_id", "position_id", "symbol"]


def positions(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse partial-close rows into one row per position."""
    if df.empty:
        return df
    key = POSITION_KEY
    d = df.copy()
    d["position_id"] = d["position_id"].fillna(-d["source_row_id"])
    d["session_id"] = d["session_id"].fillna(-1) if "session_id" in d else -1
    d["_exit_w"] = d["exit_price"] * d["notional_usd"]
    g = d.groupby(key, dropna=False)
    out = g.agg(
        direction=("direction", "first"),
        strategy_id=("strategy_id", "first"), strategy_name=("strategy_name", "first"),
        signal_price=("signal_price", "first"), entry_price=("entry_price", "first"),
        signal_bucket_ts=("signal_bucket_ts", "first"), opened_at=("opened_at", "min"),
        closed_at=("closed_at", "max"), notional_usd=("notional_usd", "sum"),
        pnl_usd=("pnl_usd", "sum"), fee_usd=("fee_usd", "sum"),
        funding_usd=("funding_usd", "sum"), exit_w=("_exit_w", "sum"), n_rows=("source_row_id", "count"),
    ).reset_index()
    out["exit_vwap"] = out["exit_w"] / out["notional_usd"]
    s = _sign(out["direction"])
    out["entry_slip_bps"] = s * (out["entry_price"] - out["signal_price"]) / out["signal_price"] * 1e4
    out["fee_bps_round_trip"] = out["fee_usd"] / out["notional_usd"] * 1e4
    out["funding_bps"] = out["funding_usd"].fillna(0) / out["notional_usd"] * 1e4
    out["net_bps"] = out["pnl_usd"] / out["notional_usd"] * 1e4
    out["ideal_bps"] = s * (out["exit_vwap"] - out["signal_price"]) / out["signal_price"] * 1e4
    out["signal_to_fill_min"] = (out["opened_at"] - out["signal_bucket_ts"]).dt.total_seconds() / 60
    return out.drop(columns=["exit_w"])


def _dist(x: pd.Series, w: pd.Series | None = None) -> dict:
    x = x.replace([np.inf, -np.inf], np.nan).dropna()
    if x.empty:
        return {"n": 0}
    out = {"n": int(len(x)), "mean": round(float(x.mean()), 3), "median": round(float(x.median()), 3),
           "p75": round(float(x.quantile(.75)), 3), "p90": round(float(x.quantile(.9)), 3),
           "p99": round(float(x.quantile(.99)), 3), "std": round(float(x.std(ddof=1)), 3) if len(x) > 1 else 0.0}
    if w is not None:
        ww = w.reindex(x.index).fillna(0)
        if ww.sum() > 0:
            out["notional_weighted_mean"] = round(float((x * ww).sum() / ww.sum()), 3)
    return out


def calibrate(df: pd.DataFrame) -> dict:
    """Measured cost model from fills -> numbers that replace guessed Config values."""
    df, excluded = clean(df)
    p = positions(df)
    p = p[p["signal_price"].notna() & (p["signal_price"] > 0) & (p["notional_usd"] > 0)]
    if p.empty:
        return {"error": "no positions with signal_price", "n_positions": 0}
    slip = _dist(p["entry_slip_bps"], p["notional_usd"])
    fee = _dist(p["fee_bps_round_trip"], p["notional_usd"])
    fund = _dist(p["funding_bps"], p["notional_usd"])
    slip_bps = max(0.0, slip.get("notional_weighted_mean", slip["mean"]))
    fee_side = fee.get("notional_weighted_mean", fee["mean"]) / 2
    warnings = [
        "Only FILLED orders are in a fill log. Limit entries that never filled (price ran away) are "
        "invisible, so measured entry slippage understates the true cost of a limit-entry strategy.",
        "Exit slippage is not measurable: the log has no exit decision price. Only entry slippage is calibrated.",
    ]
    if slip.get("p90", 0) > 3 * max(slip_bps, 0.5):
        warnings.append(f"Slippage tail is heavy (p90 {slip['p90']} bps vs mean {slip_bps:.2f}); "
                        "the mean understates bad days.")
    return {
        "n_positions": int(len(p)),
        "n_rows": int(p["n_rows"].sum()),
        "window": [str(p["opened_at"].min()), str(p["opened_at"].max())],
        "by_venue": {v: int(n) for v, n in p["venue"].value_counts().items()},
        "entry_slippage_bps": slip,
        "fee_bps_round_trip": fee,
        "funding_bps_per_position": fund,
        "signal_to_fill_minutes": _dist(p["signal_to_fill_min"]),
        "recommended_config": {"slippage_bps": round(slip_bps, 3), "fee_bps": round(fee_side, 3)},
        "empirical_slippage_bps": [round(float(v), 4) for v in p["entry_slip_bps"].dropna().tolist()],
        "warnings": warnings + ([f"{len(excluded)} rows excluded as impossible prices; "
                                 "see excluded_rows."] if excluded else []),
        "excluded_rows": excluded,
    }


def shortfall(df: pd.DataFrame) -> dict:
    """Where the edge went: ideal (signal->exit) vs what the account kept."""
    df, excluded = clean(df)
    p = positions(df)
    p = p[p["signal_price"].notna() & (p["notional_usd"] > 0)]
    if p.empty:
        return {"n_positions": 0}
    w = p["notional_usd"]
    wm = lambda s: float((s.fillna(0) * w).sum() / w.sum())  # noqa: E731
    ideal, net = wm(p["ideal_bps"]), wm(p["net_bps"])
    parts = {"entry_slippage": wm(p["entry_slip_bps"]), "fees": wm(p["fee_bps_round_trip"]),
             "funding": wm(p["funding_bps"])}
    parts["residual"] = ideal - net - sum(parts.values())
    return {
        "n_positions": int(len(p)),
        "ideal_bps_per_position": round(ideal, 3),
        "net_bps_per_position": round(net, 3),
        "shortfall_bps": {k: round(v, 3) for k, v in parts.items()},
        "edge_consumed_pct": round((ideal - net) / ideal * 100, 1) if ideal > 0 else None,
        "note": "residual = exit slippage + leverage/size rounding + anything the log does not itemise.",
        "excluded_rows": excluded,
    }


def venue_gap(df: pd.DataFrame, a: str, b: str) -> dict:
    """Same signals on two venues (e.g. pbfinance vs binance): does the fake mirror the real?"""
    df, excluded = clean(df)
    p = positions(df)
    key = ["symbol", "direction", "signal_bucket_ts"]
    pa, pb = p[p["venue"] == a], p[p["venue"] == b]
    m = pa.merge(pb, on=key, suffixes=(f"_{a}", f"_{b}"))
    out = {"venues": [a, b], "positions": {a: int(len(pa)), b: int(len(pb))}, "matched": int(len(m)),
           f"only_{a}": int(len(pa) - len(m)), f"only_{b}": int(len(pb) - len(m))}
    if len(m):
        for col in ("entry_slip_bps", "net_bps", "fee_bps_round_trip"):
            d = m[f"{col}_{a}"] - m[f"{col}_{b}"]
            out[f"{col}_diff_{a}_minus_{b}"] = _dist(d)
    out["excluded_rows"] = excluded
    out["read"] = ("Unmatched positions mean the venues disagree on WHETHER a trade happened (fill model); "
                   "matched diffs show how much they disagree on price.")
    return out


def performance(df: pd.DataFrame, by: str = "strategy_name") -> dict:
    """Per-strategy scoreboard from real fills: trades, win rate, PnL, ROI.

    ROI is on margin (size_usd = notional / leverage), the capital actually
    committed. Net bps is on notional, the number the cost model speaks.
    """
    df, excluded = clean(df)
    p = positions(df)
    if p.empty:
        return {"rows": [], "excluded_rows": excluded}
    d = df.assign(position_id=df["position_id"].fillna(-df["source_row_id"]),
                  session_id=df["session_id"].fillna(-1) if "session_id" in df else -1)
    margin = d.groupby(POSITION_KEY, dropna=False)["size_usd"].sum().rename("margin_usd")
    p = p.join(margin, on=POSITION_KEY)

    def agg(g: pd.DataFrame) -> dict:
        wins, losses = g.loc[g["pnl_usd"] > 0, "pnl_usd"], g.loc[g["pnl_usd"] < 0, "pnl_usd"]
        m = float(g["margin_usd"].sum())
        notional = float(g["notional_usd"].sum())
        return {
            "trades": int(len(g)),
            "win_rate": round(float((g["pnl_usd"] > 0).mean()), 4),
            "pnl_usd": round(float(g["pnl_usd"].sum()), 2),
            "fees_usd": round(float(g["fee_usd"].sum()), 2),
            "roi_on_margin_pct": round(float(g["pnl_usd"].sum()) / m * 100, 2) if m > 0 else None,
            "net_bps_on_notional": round(float(g["pnl_usd"].sum()) / notional * 1e4, 2) if notional > 0 else None,
            "profit_factor": round(float(wins.sum() / -losses.sum()), 3) if len(losses) and losses.sum() < 0 else None,
            "avg_win_usd": round(float(wins.mean()), 2) if len(wins) else None,
            "avg_loss_usd": round(float(losses.mean()), 2) if len(losses) else None,
            "best_usd": round(float(g["pnl_usd"].max()), 2),
            "worst_usd": round(float(g["pnl_usd"].min()), 2),
            "first": str(g["opened_at"].min()), "last": str(g["closed_at"].max()),
        }

    rows = [{by: k, **agg(g)} for k, g in p.groupby(by, dropna=False)]
    rows.sort(key=lambda r: r["pnl_usd"])
    return {"total": agg(p), "rows": rows, "excluded_rows": excluded}
