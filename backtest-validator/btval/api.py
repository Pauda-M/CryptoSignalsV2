"""HTTP surface. Stateless: send data, get a verdict. No access to the trading stack."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Literal

import pandas as pd
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import __version__
from .config import Config, Gates
from .critic import LLM_CRITIC_PROMPT
from .data import normalize_bars, series_from_records
from .health import health_check
from .pipeline import validate_signal, validate_strategy
from .sizing import position_size, streak_table
from . import fills as fillmod
from . import paper
from .stats import deflated_sharpe
from .store import Store
from .strategies import list_strategies
from .venue import NotASimulator, SimVenue

@lru_cache(maxsize=1)
def _store_singleton() -> Store:
    return Store()


def get_store() -> Store:
    return _store_singleton()


def get_venue() -> SimVenue:
    url = os.environ.get("BTVAL_SIM_URL")
    if not url:
        raise HTTPException(503, "BTVAL_SIM_URL not set (pbFinance base url, e.g. http://binance-simulator:8976)")
    try:
        return SimVenue(url, os.environ.get("BTVAL_SIM_API_KEY", ""), os.environ.get("BTVAL_SIM_API_SECRET", ""))
    except NotASimulator as e:
        raise HTTPException(403, str(e))


app = FastAPI(title="btval", version=__version__,
              description="Backtest validation: critic, deflated Sharpe, walk-forward, sizing, live health.")


class Bar(BaseModel):
    timestamp: str | int | float
    close: float


class UniverseItem(BaseModel):
    symbol: str
    listed: str | None = None
    delisted: str | None = None


class ConfigIn(BaseModel):
    fee_bps: float = 5.0
    slippage_bps: float = 3.0
    max_leverage: float = 1.0
    execution_lag: int = Field(1, ge=1)
    periods_per_year: float | None = None
    initial_capital: float = 10_000.0


class GatesIn(BaseModel):
    dsr_min: float = 0.95
    wf_min_positive_fold_ratio: float = 0.6
    wf_min_worst_fold_sharpe: float | None = None
    wf_min_oos_sharpe: float = 0.0
    implausible_sharpe_warn: float = 2.0
    implausible_sharpe_fail: float = 3.0
    lag2_retained_min: float = 0.25


class DataIn(BaseModel):
    calibration_id: int | None = Field(None, description="Use measured fee/slippage from a stored calibration.")
    persist: bool = True
    bars: list[Bar] = Field(min_length=50)
    bar_label: Literal["open", "close"] = Field(
        description="What the timestamp marks. Exchange klines are usually 'open'.")
    config: ConfigIn = ConfigIn()
    gates: GatesIn = GatesIn()
    universe: list[UniverseItem] | None = None


class StrategyReq(DataIn):
    strategy: str
    prior_trials: int = Field(0, ge=0, description="Variations tried before this run. Every one counts.")
    trial_log: list[float] | None = Field(None, description="Per-period Sharpes of prior trials.")
    train_bars: int = 365
    test_bars: int = 90
    anchored: bool = False


class SignalReq(DataIn):
    signal: list[float]
    n_trials: int = Field(ge=1)
    trial_log: list[float] | None = None
    holdout_start: str | None = Field(None, description="Date after which the rules were frozen.")
    fold_bars: int = 90
    source: str | None = Field(None, description="Signal code for the static repainting scan.")
    backtest_source: str | None = Field(None, description="Your own backtest code, scanned for shift/costs.")
    n_params: int | None = None


class DSRReq(BaseModel):
    sharpe_per_period: float
    n_trials: int = Field(ge=1)
    n_obs: int = Field(ge=3)
    skew: float = 0.0
    kurtosis: float = 3.0
    trial_sharpes: list[float] | None = None


class SizeReq(BaseModel):
    capital: float
    entry: float
    stop: float
    risk_pct: float = 0.01
    max_position_pct: float = 0.20
    fee_bps: float = 5.0
    slippage_bps: float = 3.0
    win_rate: float | None = None
    trades_per_year: int | None = None


class MonitorReq(BaseModel):
    live_returns: list[float] = Field(description="Per-bar net simple returns since deployment.")
    kill_conditions: dict


def _config(req: DataIn, store: Store) -> tuple[Config, dict | None]:
    cfg = Config(**req.config.model_dump())
    if req.calibration_id is None:
        return cfg, None
    cal = store.get_calibration(req.calibration_id)
    if cal is None:
        raise HTTPException(404, f"calibration {req.calibration_id} not found")
    rec = cal["result"]["recommended_config"]
    cfg.fee_bps, cfg.slippage_bps = float(rec["fee_bps"]), float(rec["slippage_bps"])
    return cfg, {"calibration_id": req.calibration_id, **rec}


def _prices(req: DataIn) -> tuple[pd.Series, list[str]]:
    s = series_from_records([b.model_dump() for b in req.bars])
    return normalize_bars(s, req.bar_label)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/strategies")
def strategies():
    return list_strategies()


@app.get("/critic/prompt")
def critic_prompt():
    return {"prompt": LLM_CRITIC_PROMPT}


@app.post("/validate/strategy")
def post_validate_strategy(req: StrategyReq, store: Store = Depends(get_store)):
    prices, notes = _prices(req)
    cfg, cal = _config(req, store)
    try:
        rep = validate_strategy(
            prices, req.strategy, cfg, Gates(**req.gates.model_dump()),
            prior_trials=req.prior_trials, trial_log=req.trial_log, train_bars=req.train_bars,
            test_bars=req.test_bars, anchored=req.anchored, bar_label="close",
            universe=[u.model_dump() for u in req.universe] if req.universe else None)
    except (KeyError, ValueError) as e:
        raise HTTPException(422, str(e))
    rep["data_notes"] = notes
    rep["calibration"] = cal
    if req.persist:
        rep["run_id"] = store.save_run("strategy", req.strategy, rep, req.prior_trials)
    return rep


@app.post("/validate/signal")
def post_validate_signal(req: SignalReq, store: Store = Depends(get_store)):
    if len(req.signal) != len(req.bars):
        raise HTTPException(422, "signal and bars must have the same length")
    raw = series_from_records([b.model_dump() for b in req.bars])
    df, notes = normalize_bars(pd.DataFrame({"close": raw, "signal": req.signal}, index=raw.index),
                               req.bar_label)
    prices, sig = df["close"], df["signal"]
    cfg, cal = _config(req, store)
    try:
        rep = validate_signal(
            prices, sig, cfg, Gates(**req.gates.model_dump()),
            n_trials=req.n_trials, trial_log=req.trial_log, holdout_start=req.holdout_start,
            fold_bars=req.fold_bars, source=req.source, backtest_source=req.backtest_source,
            n_params=req.n_params, bar_label="close",
            universe=[u.model_dump() for u in req.universe] if req.universe else None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    rep["data_notes"] = notes
    rep["calibration"] = cal
    if req.persist:
        rep["run_id"] = store.save_run("signal", "precomputed", rep, req.n_trials)
    return rep


@app.post("/stats/deflated-sharpe")
def post_dsr(req: DSRReq):
    return deflated_sharpe(req.sharpe_per_period, req.n_trials, req.n_obs, req.skew,
                           req.kurtosis, trial_sharpes=req.trial_sharpes)


@app.post("/size")
def post_size(req: SizeReq):
    try:
        out = {"position": position_size(req.capital, req.entry, req.stop, req.risk_pct,
                                         req.max_position_pct, req.fee_bps, req.slippage_bps)}
    except ValueError as e:
        raise HTTPException(422, str(e))
    if req.win_rate is not None and req.trades_per_year:
        out["streaks"] = streak_table(req.win_rate, req.trades_per_year)
    return out


@app.post("/monitor")
def post_monitor(req: MonitorReq):
    r = pd.Series(req.live_returns, dtype=float)
    required = {"expected_sr_per_period", "max_dd_pct_limit", "decay_fraction", "min_window", "alpha"}
    if missing := required - req.kill_conditions.keys():
        raise HTTPException(422, f"kill_conditions missing {sorted(missing)}; use the block from a DEPLOYABLE report")
    return health_check(r, req.kill_conditions)


# ---------------------------------------------------------------- runs
@app.get("/runs")
def get_runs(limit: int = 50, store: Store = Depends(get_store)):
    return store.list_runs(limit)


@app.get("/runs/{run_id}")
def get_run(run_id: int, store: Store = Depends(get_store)):
    r = store.get_run(run_id)
    if r is None:
        raise HTTPException(404, "not found")
    return r


# ---------------------------------------------------------------- fills
class IngestReq(BaseModel):
    venue: str = Field(description="'binance' for real fills, 'pbfinance' for simulator fills. You decide; the log cannot tell.")
    source_db: str = Field(description="Free-text label for where the rows came from.")
    rows: list[dict[str, Any]]


class FillFilter(BaseModel):
    venue: str | None = None
    strategy_id: int | None = None
    symbol: str | None = None
    since: str | None = None
    until: str | None = None


@app.post("/ingest/trades")
def post_ingest(req: IngestReq, store: Store = Depends(get_store)):
    for r in req.rows:
        r.pop("api_key_ref", None)
        r.pop("user_id", None)
        if "source_row_id" not in r and "id" not in r:
            raise HTTPException(422, "each row needs id or source_row_id")
    return store.upsert_fills(req.rows, req.venue, req.source_db)


def _fills(f: FillFilter, store: Store) -> pd.DataFrame:
    df = store.load_fills(f.venue, f.strategy_id, f.symbol, f.since, f.until)
    if df.empty:
        raise HTTPException(404, "no fills match")
    return df


@app.post("/fills/calibrate")
def post_calibrate(f: FillFilter, save: bool = True, store: Store = Depends(get_store)):
    res = fillmod.calibrate(_fills(f, store))
    if save and "error" not in res:
        res["calibration_id"] = store.save_calibration(f.model_dump(), res)
    samples = res.pop("empirical_slippage_bps", [])  # stored with the calibration, too long to echo
    res["n_empirical_samples"] = len(samples)
    return res


@app.get("/fills/performance")
def get_performance(venue: str | None = None, strategy_id: int | None = None, symbol: str | None = None,
                    since: str | None = None, until: str | None = None, by: Literal["strategy_name", "symbol"] = "strategy_name",
                    store: Store = Depends(get_store)):
    df = store.load_fills(venue, strategy_id, symbol, since, until)
    if df.empty:
        return {"total": None, "rows": [], "excluded_rows": []}
    return fillmod.performance(df, by)


@app.post("/fills/shortfall")
def post_shortfall(f: FillFilter, store: Store = Depends(get_store)):
    return fillmod.shortfall(_fills(f, store))


@app.post("/fills/venue-gap")
def post_venue_gap(f: FillFilter, a: str = "pbfinance", b: str = "binance", store: Store = Depends(get_store)):
    return fillmod.venue_gap(_fills(FillFilter(**{**f.model_dump(), "venue": None}), store), a, b)


# ---------------------------------------------------------------- paper
class PaperReq(BaseModel):
    strategy: str
    params: dict[str, Any] = {}
    symbol: str
    interval: str = "1d"
    validation_run_id: int | None = None
    allow_unvalidated: bool = False
    calibration_id: int | None = None
    cost_mode: Literal["fixed", "empirical", "none"] = "fixed"
    slippage_bps: float | None = None
    fee_bps: float | None = None
    initial_capital: float = 10_000.0
    max_leverage: float = 1.0
    max_order_notional: float = 5_000.0
    rebalance_band_pct: float = Field(5.0, ge=0, le=50)


@app.post("/paper/sessions")
def post_paper_session(req: PaperReq, store: Store = Depends(get_store)):
    url = os.environ.get("BTVAL_SIM_URL", "")
    if not url:
        raise HTTPException(503, "pbFinance is not configured on this btval (BTVAL_SIM_URL unset). "
                                 "Paper sessions need the simulator; nothing was created.")
    cost: dict[str, Any] = {"mode": req.cost_mode}
    if req.calibration_id is not None:
        cal = store.get_calibration(req.calibration_id)
        if cal is None:
            raise HTTPException(404, "calibration not found")
        rec = cal["result"]["recommended_config"]
        cost.update(slippage_bps=rec["slippage_bps"], fee_bps=rec["fee_bps"],
                    samples=cal["result"].get("empirical_slippage_bps"), calibration_id=req.calibration_id)
    if req.slippage_bps is not None:
        cost["slippage_bps"] = req.slippage_bps
    if req.fee_bps is not None:
        cost["fee_bps"] = req.fee_bps
    if "fee_bps" not in cost:
        raise HTTPException(422, "need calibration_id or explicit fee_bps/slippage_bps")
    params = req.params
    if not params and req.validation_run_id is not None:
        run = store.get_run(req.validation_run_id)
        params = ((run or {}).get("report") or {}).get("strategy", {}).get("in_sample_best") or {}
    try:
        sid = paper.create_session(store, strategy=req.strategy, params=params, symbol=req.symbol,
                                   interval=req.interval, venue_url=url, cost_model=cost,
                                   initial_capital=req.initial_capital, max_leverage=req.max_leverage,
                                   max_order_notional=req.max_order_notional,
                                   rebalance_band_pct=req.rebalance_band_pct,
                                   validation_run_id=req.validation_run_id,
                                   allow_unvalidated=req.allow_unvalidated)
    except NotASimulator as e:
        raise HTTPException(403, str(e))
    except (KeyError, ValueError) as e:
        raise HTTPException(422, str(e))
    return {"session_id": sid}


@app.post("/paper/sessions/{session_id}/tick")
def post_tick(session_id: int, store: Store = Depends(get_store), venue: SimVenue = Depends(get_venue)):
    try:
        return paper.tick(store, venue, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/paper/sessions")
def get_paper_sessions(store: Store = Depends(get_store)):
    return paper.list_sessions(store)


@app.get("/paper/sessions/{session_id}/equity")
def get_paper_equity(session_id: int, store: Store = Depends(get_store)):
    return paper.equity_series(store, session_id)


@app.get("/paper/sessions/{session_id}/orders")
def get_paper_orders(session_id: int, limit: int = 200, store: Store = Depends(get_store)):
    led = paper.ledger(store, session_id)
    if led.empty:
        return []
    led = led.drop(columns=["venue_raw"]).tail(limit).iloc[::-1]
    return json.loads(led.to_json(orient="records", date_format="iso"))


@app.get("/calibrations")
def get_calibrations(limit: int = 20, store: Store = Depends(get_store)):
    return store.list_calibrations(limit)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return HTMLResponse((Path(__file__).parent / "static" / "dashboard.html").read_text(encoding="utf-8"))


@app.get("/paper/sessions/{session_id}")
def get_paper(session_id: int, store: Store = Depends(get_store)):
    try:
        return paper.report(store, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
