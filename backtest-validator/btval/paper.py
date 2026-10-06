"""Forward paper trading on pbFinance, logged to btval's own store.

Per closed bar: compute the validated strategy's signal, size the target,
send a MARKET order to the simulator, then book a REALISTIC fill:

    realistic = venue_avg_price  moved adversely by  slippage_bps (calibrated)
    fee       = |qty| * realistic * fee_bps (calibrated, per side)

Both the raw simulator fill and the realistic fill are stored, plus the drift
between the decision price (last close) and the simulator fill, which is the
measured version of the backtest's fill assumption.

Guarantees:
  * one decision per (session, bar, kind); the row is reserved BEFORE the
    order is sent, and the client order id is deterministic, so a crash or a
    second runner cannot double-order;
  * the session must reference a DEPLOYABLE validation run, or be explicitly
    created as unvalidated (and is labelled so forever);
  * kill conditions from the validation run are checked after every bar; a
    HALT flattens the position and stops the session.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from .health import health_check
from .store import Store, paper_equity, paper_marks, paper_orders, paper_sessions
from .strategies import get_strategy
from .venue import SimVenue, assert_sim_url


def _now():
    return datetime.now(timezone.utc)


def create_session(store: Store, *, strategy: str, params: dict, symbol: str, interval: str,
                   venue_url: str, cost_model: dict, initial_capital: float = 10_000.0,
                   max_leverage: float = 1.0, max_order_notional: float = 5_000.0,
                   rebalance_band_pct: float = 5.0,
                   validation_run_id: int | None = None, allow_unvalidated: bool = False) -> int:
    assert_sim_url(venue_url)
    get_strategy(strategy)  # must exist
    kill = None
    if validation_run_id is not None:
        run = store.get_run(validation_run_id)
        if run is None:
            raise ValueError(f"validation run {validation_run_id} not found")
        if run["subject"] != strategy:
            raise ValueError(f"run {validation_run_id} validated {run['subject']!r}, not {strategy!r}")
        if run["verdict"] != "DEPLOYABLE" and not allow_unvalidated:
            raise ValueError(f"run {validation_run_id} verdict is {run['verdict']}; refusing to paper-trade it")
        kill = run["kill_conditions"]
        if kill is None:
            # A rejected run carries no kill conditions; an unvalidated session
            # still gets a stop, derived from the run's out-of-sample stats.
            oos = ((run.get("report") or {}).get("walk_forward") or {}).get("oos_metrics") or {}
            if "sharpe_per_period" in oos and "max_drawdown_pct" in oos:
                from .health import kill_conditions
                kill = kill_conditions(oos)
    elif not allow_unvalidated:
        raise ValueError("validation_run_id required (or allow_unvalidated=true, which is recorded)")
    mode = cost_model.get("mode", "fixed")
    if mode not in ("fixed", "empirical", "none"):
        raise ValueError("cost_model.mode must be fixed | empirical | none")
    if mode == "empirical" and not cost_model.get("samples"):
        raise ValueError("empirical cost model needs samples (from a calibration)")
    with store.engine.begin() as cx:
        res = cx.execute(insert(paper_sessions).values(
            created_at=_now(), status="active", strategy=strategy, params=params, symbol=symbol,
            interval=interval, venue_host=urllib.parse.urlsplit(venue_url).hostname,
            initial_capital=initial_capital, max_leverage=max_leverage,
            max_order_notional=max_order_notional,
            cost_model={**cost_model, "rebalance_band_pct": rebalance_band_pct}, kill_conditions=kill,
            validation_run_id=validation_run_id, unvalidated=validation_run_id is None or
            (store.get_run(validation_run_id) or {}).get("verdict") != "DEPLOYABLE"))
        return int(res.inserted_primary_key[0])


_INTERVAL_MIN = {"15m": 15, "1h": 60, "4h": 240, "12h": 720, "1d": 1440}


def load_bars(venue: SimVenue, symbol: str, interval: str, n: int) -> pd.Series:
    """Closed bars for the decision.

    With BTVAL_BARS_DSN set, bars come from pbMasterData's live OHLCV aggregates
    (read-only): pbFinance's /klines aggregates anything >= 1h into HOURLY
    buckets, so a '1d' request there returns hourly bars labelled daily.
    Without it, the venue's klines are used (correct for < 1h only).
    """
    import os

    dsn = os.environ.get("BTVAL_BARS_DSN")
    if not dsn:
        return venue.klines(symbol, interval, limit=n)
    from .data import load_pg_bars, pair_id_for
    mins = _INTERVAL_MIN.get(interval)
    if mins is None:
        raise ValueError(f"unsupported interval {interval}; use one of {list(_INTERVAL_MIN)}")
    since = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=mins * (n + 5))).strftime("%Y-%m-%d %H:%M")
    s, _ = load_pg_bars(dsn, f"master_data.cagg_ohlcv_{mins}m", pair_id_for(dsn, symbol), "open", since,
                        now=pd.Timestamp(venue.clock(), unit="s", tz="UTC"))
    return s


def _slippage_bps(cost: dict, session_id: int, bar_ts: pd.Timestamp) -> float:
    mode = cost.get("mode", "fixed")
    if mode == "none":
        return 0.0
    if mode == "empirical":
        rng = np.random.default_rng([session_id, int(bar_ts.timestamp())])
        return float(max(0.0, rng.choice(np.asarray(cost["samples"], dtype=float))))
    return float(cost.get("slippage_bps", 0.0))


def ledger(store: Store, session_id: int) -> pd.DataFrame:
    with store.engine.connect() as cx:
        df = pd.read_sql(select(paper_orders).where(paper_orders.c.session_id == session_id)
                         .order_by(paper_orders.c.bar_ts, paper_orders.c.id), cx)
    if not df.empty:
        df["bar_ts"] = pd.to_datetime(df["bar_ts"], utc=True)
    return df


def _position_and_cash(sess: dict, led: pd.DataFrame) -> tuple[float, float]:
    f = led[led["status"] == "filled"] if not led.empty else led
    if f.empty:
        return 0.0, float(sess["initial_capital"])
    qty = float(f["venue_executed_qty"].sum())
    cash = float(sess["initial_capital"] - (f["venue_executed_qty"] * f["realistic_price"]).sum() - f["fee_usd"].sum())
    return qty, cash


def equity_curve(sess: dict, led: pd.DataFrame, prices: pd.Series) -> pd.Series:
    """Mark-to-market per bar from the first decision bar onward."""
    if led.empty:
        return pd.Series(dtype=float)
    px = prices[prices.index >= led["bar_ts"].min()]
    if px.empty:
        return pd.Series(dtype=float)
    f = led[led["status"] == "filled"] if not led.empty else led
    eq = []
    for ts, p in px.items():
        done = f[f["bar_ts"] <= ts] if not f.empty else f
        q = float(done["venue_executed_qty"].sum()) if not done.empty else 0.0
        c = sess["initial_capital"] - (float((done["venue_executed_qty"] * done["realistic_price"]).sum()
                                             + done["fee_usd"].sum()) if not done.empty else 0.0)
        eq.append(c + q * p)
    return pd.Series(eq, index=px.index)


MAX_ATTEMPTS = 3


def _place(store: Store, venue: SimVenue, sess: dict, bar_ts: pd.Timestamp, kind: str,
           signal: float | None, target_qty: float, cur_qty: float, price: float) -> dict:
    sid = sess["id"]
    coid = f"btval-{sid}-{int(bar_ts.timestamp())}-{kind[0]}"
    row = dict(session_id=sid, bar_ts=bar_ts.to_pydatetime(), created_at=_now(), status="pending",
               kind=kind, symbol=sess["symbol"], signal=signal, target_qty=target_qty, prev_qty=cur_qty,
               decision_price=price, client_order_id=coid)
    attempt = 1
    try:
        with store.engine.begin() as cx:  # reserve the decision first
            oid = cx.execute(insert(paper_orders).values(**row)).inserted_primary_key[0]
    except IntegrityError:
        # A decision that errored before any fill may be retried (bounded); a
        # filled / no_trade / pending decision is final for this bar.
        with store.engine.begin() as cx:
            prev = cx.execute(select(paper_orders).where(
                paper_orders.c.session_id == sid, paper_orders.c.bar_ts == row["bar_ts"],
                paper_orders.c.kind == kind)).first()
            prev = dict(prev._mapping) if prev else None
            attempts = (prev.get("note") or "").count("attempt ") + 1 if prev else 0
            if not prev or prev["status"] != "error" or prev["venue_order_id"] or attempts >= MAX_ATTEMPTS:
                return {"status": "already_decided", "bar_ts": str(bar_ts), "kind": kind}
            cx.execute(update(paper_orders).where(paper_orders.c.id == prev["id"]).values(
                status="pending", created_at=_now(), signal=signal, target_qty=target_qty, prev_qty=cur_qty,
                decision_price=price, note=f"{prev['note']} | attempt {attempts + 1}"))
            oid = prev["id"]
            attempt = attempts + 1

    filt = venue.filters(sess["symbol"])
    delta = target_qty - cur_qty
    note = []
    # The cap limits how fast a SIGNAL can build exposure. It must never stop a
    # halt from flattening: a capped exit is a halt that leaves risk on.
    if kind == "signal" and abs(delta) * price > sess["max_order_notional"]:
        delta = np.sign(delta) * sess["max_order_notional"] / price
        note.append("clipped to max_order_notional")
    qty = filt.round_qty(delta)
    upd: dict = {"order_qty": qty}
    # Rebalance band: re-sizing to drifting equity every bar pays fees on noise
    # the backtest (which holds a constant fraction) never charges. Signal
    # orders smaller than the band are skipped; halts and flips never are.
    band = float(sess["cost_model"].get("rebalance_band_pct", 0.0)) / 100
    flip = np.sign(target_qty) != np.sign(cur_qty)
    if kind == "signal" and not flip and abs(delta) < band * max(abs(target_qty), abs(cur_qty)):
        upd.update(status="no_trade", order_qty=0.0, note=f"inside {band:.0%} rebalance band")
    elif qty == 0 or abs(qty) < filt.min_qty or abs(qty) * price < filt.min_notional:
        upd.update(status="no_trade", note="; ".join(note + ["below venue minimum / no change"]))
    else:
        try:
            # Reduce first with reduceOnly, then open the remainder as its own
            # order. One-way Binance nets either way; pbFinance only nets
            # correctly with reduceOnly, and drops the excess of a flip.
            legs = []
            if cur_qty and np.sign(qty) != np.sign(cur_qty):
                red = filt.round_qty(np.sign(qty) * min(abs(qty), abs(cur_qty)))
                if red:
                    legs.append((red, True))
                rest = filt.round_qty(qty - red)
                if rest:
                    legs.append((rest, False))
            else:
                legs.append((qty, False))
            exe_total = notional = 0.0
            raws = []
            for i, (lq, ro) in enumerate(legs):
                r = venue.market_order(sess["symbol"], lq, f"{coid}-a{attempt}-{i}", reduce_only=ro)
                raws.append(r)
                ex = float(r["executedQty"]) * np.sign(lq)
                exe_total += ex
                notional += abs(ex) * (float(r.get("avgPrice") or 0) or price)
            avg = notional / abs(exe_total) if exe_total else price
            exe = exe_total
            r = {"orderId": ",".join(str(x.get("orderId")) for x in raws), "status": "FILLED", "legs": raws}
            sign = 1.0 if qty > 0 else -1.0
            slip = _slippage_bps(sess["cost_model"], sid, bar_ts)
            real = avg * (1 + sign * slip / 1e4)
            fee = abs(exe) * real * float(sess["cost_model"].get("fee_bps", 0.0)) / 1e4
            upd.update(status="filled", venue_order_id=str(r.get("orderId")), venue_status=r.get("status"),
                       venue_avg_price=avg, venue_executed_qty=exe,
                       venue_drift_bps=sign * (avg - price) / price * 1e4,
                       slippage_bps_applied=slip, realistic_price=float(real), fee_usd=float(fee),
                       note="; ".join(note) or None, venue_raw=r)
        except Exception as e:  # noqa: BLE001 -- recorded, never swallowed silently
            upd.update(status="error", note=f"{type(e).__name__}: {e}")
    with store.engine.connect() as cx:
        prior = cx.execute(select(paper_orders.c.note).where(paper_orders.c.id == oid)).scalar()
    if prior:  # keep the retry history; append this attempt's outcome
        upd["note"] = f"{prior} -> {upd['note']}" if upd.get("note") else prior
    with store.engine.begin() as cx:
        cx.execute(update(paper_orders).where(paper_orders.c.id == oid).values(**upd))
    return {"status": upd["status"], "bar_ts": str(bar_ts), "kind": kind, "order_qty": qty,
            "decision_price": price, **{k: upd.get(k) for k in ("venue_avg_price", "realistic_price",
                                                                  "venue_drift_bps", "fee_usd", "note")}}


def tick(store: Store, venue: SimVenue, session_id: int) -> dict:
    with store.engine.connect() as cx:
        r = cx.execute(select(paper_sessions).where(paper_sessions.c.id == session_id)).first()
    if r is None:
        raise ValueError(f"paper session {session_id} not found")
    sess = dict(r._mapping)
    if sess["status"] != "active":
        return {"session": session_id, "status": sess["status"], "reason": sess["halted_reason"]}
    if urllib.parse.urlsplit(venue.base).hostname != sess["venue_host"]:
        raise RuntimeError("venue host differs from the one this session was created on")

    strat = get_strategy(sess["strategy"])
    prices = load_bars(venue, sess["symbol"], sess["interval"], max(strat.warmup + 50, 300))
    bar_ts, price = prices.index[-1], float(prices.iloc[-1])
    sig = float(np.clip(strat.signal(prices, **sess["params"]).iloc[-1],
                        -sess["max_leverage"], sess["max_leverage"]))

    led = ledger(store, session_id)
    cur_qty, cash = _position_and_cash(sess, led)
    equity = cash + cur_qty * price
    out = {"session": session_id, "bar_ts": str(bar_ts), "signal": sig, "equity": round(equity, 2)}
    out["order"] = _place(store, venue, sess, bar_ts, "signal", sig, sig * max(equity, 0) / price, cur_qty, price)

    try:
        venue_qty = venue.position_amt(sess["symbol"])
        led = ledger(store, session_id)
        book_qty, _ = _position_and_cash(sess, led)
        out["reconcile"] = {"venue_qty": venue_qty, "ledger_qty": book_qty,
                            "diverged": not np.isclose(venue_qty, book_qty, atol=1e-9)}
    except Exception as e:  # noqa: BLE001
        out["reconcile"] = {"error": str(e)}

    eq = equity_curve(sess, ledger(store, session_id), prices)
    h = None
    if sess["kill_conditions"] and len(eq):
        # first point is measured against starting capital, not the post-fill mark
        rets = pd.concat([pd.Series([eq.iloc[0] / sess["initial_capital"] - 1], index=[eq.index[0]]),
                          eq.pct_change().dropna()])
        h = health_check(rets, sess["kill_conditions"])
        out["health"] = h
    if h is not None and h["action"] == "HALT":
        q, _ = _position_and_cash(sess, ledger(store, session_id))
        out["halt_order"] = _place(store, venue, sess, bar_ts, "halt", None, 0.0, q, price)
        with store.engine.begin() as cx:
            cx.execute(update(paper_sessions).where(paper_sessions.c.id == session_id)
                       .values(status="halted", halted_reason=",".join(h["alerts"])))
    _snapshot(store, sess, bar_ts, price, sig, h, out.get("reconcile", {}).get("diverged"))
    out["live"] = _mark(store, sess, venue, price)
    return out


def _mark(store: Store, sess: dict, venue: SimVenue, fallback_price: float) -> dict:
    """Live mark-to-market at the venue's current price (display only; kill
    conditions stay on bar closes, like the backtest)."""
    try:
        px = venue.ticker_price(sess["symbol"])
    except Exception:  # noqa: BLE001 -- a missing tick must not break trading
        px = fallback_price
    q, cash = _position_and_cash(sess, ledger(store, sess["id"]))
    eq = cash + q * px
    with store.engine.begin() as cx:
        prev = cx.execute(select(paper_marks.c.peak_equity).where(paper_marks.c.session_id == sess["id"])).scalar()
        bar_peak = cx.execute(select(paper_equity.c.equity).where(paper_equity.c.session_id == sess["id"])
                              .order_by(paper_equity.c.equity.desc()).limit(1)).scalar()
        peak = max(float(prev or 0), float(bar_peak or 0), float(sess["initial_capital"]), eq)
        vals = dict(marked_at=_now(), price=px, position_qty=q, equity=eq, peak_equity=peak)
        if prev is None:
            cx.execute(insert(paper_marks).values(session_id=sess["id"], **vals))
        else:
            cx.execute(update(paper_marks).where(paper_marks.c.session_id == sess["id"]).values(**vals))
    return {"price": px, "equity": round(eq, 2), "position_qty": q}


def _snapshot(store: Store, sess: dict, bar_ts, price: float, sig: float, h: dict | None,
              diverged: bool | None) -> None:
    led = ledger(store, sess["id"])
    q, cash = _position_and_cash(sess, led)
    equity = cash + q * price
    with store.engine.connect() as cx:
        peak = cx.execute(select(paper_equity.c.equity).where(paper_equity.c.session_id == sess["id"])
                          .order_by(paper_equity.c.equity.desc()).limit(1)).scalar()
    peak = max(float(peak or 0), float(sess["initial_capital"]), equity)
    vals = dict(recorded_at=_now(), price=price, position_qty=q, equity=equity,
                drawdown_pct=(equity / peak - 1) * 100, signal=sig, action=(h or {}).get("action"),
                alerts=(h or {}).get("alerts", []), reconcile_diverged=diverged)
    # Upsert: every tick refreshes this bar's row, so a fill that lands after
    # the first attempt (retry) and the "last tick" time are both current.
    try:
        with store.engine.begin() as cx:
            cx.execute(insert(paper_equity).values(session_id=sess["id"], bar_ts=bar_ts.to_pydatetime(), **vals))
    except IntegrityError:
        with store.engine.begin() as cx:
            cx.execute(update(paper_equity).where(paper_equity.c.session_id == sess["id"],
                                                  paper_equity.c.bar_ts == bar_ts.to_pydatetime()).values(**vals))


def trade_stats(sess: dict, led: pd.DataFrame, mark: float | None = None) -> dict:
    """Round trips from the order ledger (average-cost), win rate, PnL, ROI."""
    f = led[led["status"] == "filled"].sort_values(["bar_ts", "id"]) if not led.empty else led
    pos = avg = 0.0
    realized = fees = 0.0
    trip_pnl = 0.0
    trips: list[float] = []
    for _, o in (f.iterrows() if not f.empty else []):
        q, px, fee = float(o["venue_executed_qty"]), float(o["realistic_price"]), float(o["fee_usd"] or 0)
        fees += fee
        trip_pnl -= fee
        if pos == 0 or np.sign(q) == np.sign(pos):
            avg = (avg * abs(pos) + px * abs(q)) / (abs(pos) + abs(q))
            pos += q
            continue
        closing = min(abs(q), abs(pos))
        pnl = closing * (px - avg) * np.sign(pos)
        realized += pnl
        trip_pnl += pnl
        pos += q
        if abs(pos) < 1e-12 or np.sign(pos) == np.sign(q):  # flat, or flipped through zero
            trips.append(trip_pnl)
            trip_pnl = 0.0
            avg = px if abs(pos) > 1e-12 else 0.0
    unreal = pos * (mark - avg) if (mark is not None and pos) else 0.0
    wins = [t for t in trips if t > 0]
    losses = [t for t in trips if t < 0]
    total = realized - fees + unreal
    cap = float(sess["initial_capital"])
    return {
        "round_trips": len(trips),
        "win_rate": round(len(wins) / len(trips), 4) if trips else None,
        "realized_pnl_usd": round(realized - fees, 2),
        "unrealized_pnl_usd": round(unreal, 2),
        "total_pnl_usd": round(total, 2),
        "fees_usd": round(fees, 2),
        "roi_pct": round(total / cap * 100, 3) if cap else None,
        "profit_factor": round(sum(wins) / -sum(losses), 3) if losses else None,
        "avg_win_usd": round(float(np.mean(wins)), 2) if wins else None,
        "avg_loss_usd": round(float(np.mean(losses)), 2) if losses else None,
        "open_qty": pos, "avg_entry": avg if pos else None,
    }


def list_sessions(store: Store) -> list[dict]:
    with store.engine.connect() as cx:
        sess = [dict(r._mapping) for r in cx.execute(select(paper_sessions).order_by(paper_sessions.c.id.desc()))]
        out = []
        for s in sess:
            last = cx.execute(select(paper_equity).where(paper_equity.c.session_id == s["id"])
                              .order_by(paper_equity.c.bar_ts.desc()).limit(1)).first()
            last = dict(last._mapping) if last else {}
            mdd = cx.execute(select(paper_equity.c.drawdown_pct).where(paper_equity.c.session_id == s["id"])
                             .order_by(paper_equity.c.drawdown_pct).limit(1)).scalar()
            mark = cx.execute(select(paper_marks).where(paper_marks.c.session_id == s["id"])).first()
            mark = dict(mark._mapping) if mark else None
            if mark and (not last or mark["marked_at"] >= last.get("recorded_at", mark["marked_at"])):
                live_dd = (mark["equity"] / mark["peak_equity"] - 1) * 100 if mark["peak_equity"] else 0.0
                last = {**last, "equity": mark["equity"], "price": mark["price"],
                        "position_qty": mark["position_qty"], "drawdown_pct": live_dd,
                        "recorded_at": mark["marked_at"]}
                mdd = min(mdd if mdd is not None else 0.0, live_dd)
            out.append({
                "id": s["id"], "status": s["status"], "strategy": s["strategy"], "params": s["params"],
                "live": bool(mark), "marked_at": mark["marked_at"] if mark else None,
                "symbol": s["symbol"], "interval": s["interval"], "venue_host": s["venue_host"],
                "created_at": s["created_at"], "unvalidated": s["unvalidated"],
                "validation_run_id": s["validation_run_id"], "halted_reason": s["halted_reason"],
                "initial_capital": s["initial_capital"], "cost_model": {k: v for k, v in s["cost_model"].items() if k != "samples"},
                "kill_conditions": s["kill_conditions"],
                "last_bar_ts": last.get("bar_ts"), "last_recorded_at": last.get("recorded_at"),
                "equity": last.get("equity"), "price": last.get("price"), "position_qty": last.get("position_qty"),
                "drawdown_pct": last.get("drawdown_pct"), "max_drawdown_pct": mdd,
                "return_pct": (last["equity"] / s["initial_capital"] - 1) * 100 if last else None,
                "last_action": last.get("action"), "last_alerts": last.get("alerts"),
                "reconcile_diverged": last.get("reconcile_diverged"),
                "stats": trade_stats(s, ledger(store, s["id"]), last.get("price")),
            })
    return out


def equity_series(store: Store, session_id: int) -> list[dict]:
    with store.engine.connect() as cx:
        rows = cx.execute(select(paper_equity).where(paper_equity.c.session_id == session_id)
                          .order_by(paper_equity.c.bar_ts)).all()
    return [dict(r._mapping) for r in rows]


def report(store: Store, session_id: int) -> dict:
    with store.engine.connect() as cx:
        r = cx.execute(select(paper_sessions).where(paper_sessions.c.id == session_id)).first()
    if r is None:
        raise ValueError("not found")
    sess = dict(r._mapping)
    led = ledger(store, session_id)
    f = led[led["status"] == "filled"] if not led.empty else led
    qty, cash = _position_and_cash(sess, led)
    def d(s):
        s = s.dropna()
        return {"n": int(len(s)), "mean": round(float(s.mean()), 3) if len(s) else None,
                "p90": round(float(s.quantile(.9)), 3) if len(s) else None}
    return {
        "session": {k: (str(v) if isinstance(v, datetime) else v) for k, v in sess.items()},
        "orders": {s: int(n) for s, n in led["status"].value_counts().items()} if not led.empty else {},
        "position_qty": qty, "cash": round(cash, 2),
        "venue_drift_bps": d(f["venue_drift_bps"]) if not f.empty else {"n": 0},
        "slippage_bps_applied": d(f["slippage_bps_applied"]) if not f.empty else {"n": 0},
        "fees_usd": round(float(f["fee_usd"].sum()), 2) if not f.empty else 0.0,
        "read": "venue_drift_bps is the measured gap between the backtest's fill (last close) and the "
                "simulator's fill. If it is not ~0, the backtest's fill assumption is wrong.",
    }
