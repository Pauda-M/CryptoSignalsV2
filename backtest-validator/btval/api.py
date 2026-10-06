"""HTTP surface. Stateless: send data, get a verdict. No access to the trading stack."""
from __future__ import annotations

from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .config import Config, Gates
from .critic import LLM_CRITIC_PROMPT
from .data import normalize_bars, series_from_records
from .health import health_check
from .pipeline import validate_signal, validate_strategy
from .sizing import position_size, streak_table
from .stats import deflated_sharpe
from .strategies import list_strategies

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
def post_validate_strategy(req: StrategyReq):
    prices, notes = _prices(req)
    try:
        rep = validate_strategy(
            prices, req.strategy, Config(**req.config.model_dump()), Gates(**req.gates.model_dump()),
            prior_trials=req.prior_trials, trial_log=req.trial_log, train_bars=req.train_bars,
            test_bars=req.test_bars, anchored=req.anchored, bar_label="close",
            universe=[u.model_dump() for u in req.universe] if req.universe else None)
    except (KeyError, ValueError) as e:
        raise HTTPException(422, str(e))
    rep["data_notes"] = notes
    return rep


@app.post("/validate/signal")
def post_validate_signal(req: SignalReq):
    if len(req.signal) != len(req.bars):
        raise HTTPException(422, "signal and bars must have the same length")
    raw = series_from_records([b.model_dump() for b in req.bars])
    df, notes = normalize_bars(pd.DataFrame({"close": raw, "signal": req.signal}, index=raw.index),
                               req.bar_label)
    prices, sig = df["close"], df["signal"]
    try:
        rep = validate_signal(
            prices, sig, Config(**req.config.model_dump()), Gates(**req.gates.model_dump()),
            n_trials=req.n_trials, trial_log=req.trial_log, holdout_start=req.holdout_start,
            fold_bars=req.fold_bars, source=req.source, backtest_source=req.backtest_source,
            n_params=req.n_params, bar_label="close",
            universe=[u.model_dump() for u in req.universe] if req.universe else None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    rep["data_notes"] = notes
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
