"""The critic: eight ways a backtest lies, checked by code rather than by vibes.

Every check returns status PRESENT (the error is there), ABSENT (checked and
not there), UNKNOWN (cannot be determined from what was supplied — this is
not a pass) or WARN (suspicious, human must look). Evidence is quoted source
lines ("L<n>: <code>") or measured numbers. No summaries.
"""
from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field, asdict
from typing import Callable

import numpy as np
import pandas as pd

from . import engine as _engine
from .config import Config, Gates
from .engine import backtest
from .metrics import metrics

PRESENT, ABSENT, UNKNOWN, WARN = "PRESENT", "ABSENT", "UNKNOWN", "WARN"


@dataclass
class Finding:
    id: int
    name: str
    status: str
    evidence: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# static scanning
# --------------------------------------------------------------------------
REPAINT_PATTERNS: list[tuple[str, str]] = [
    (r"\.shift\(\s*-\s*\d", "negative shift reads future bars"),
    (r"center\s*=\s*True", "centered window uses future bars"),
    (r"\b(bfill|backfill)\b|method\s*=\s*['\"](bfill|backfill)", "back-fill copies future values into the past"),
    (r"zig_?zag", "zigzag repaints its last leg"),
    (r"filtfilt|savgol_filter|gaussian_filter1d|lowess|\.interpolate\(", "two-sided smoother/interpolation"),
    (r"merge_asof\([^)]*direction\s*=\s*['\"](forward|nearest)", "as-of join pulling forward/nearest rows"),
    (r"\.iloc\[\s*\w+\s*\+\s*\d+", "positional index ahead of the current bar"),
    (r"np\.convolve\([^)]*['\"]same['\"]", "'same' convolution is centered"),
    (r"find_peaks|argrelextrema", "peak detection confirms with bars after the peak"),
]
RESAMPLE = re.compile(r"\.resample\(")
RESAMPLE_OK = re.compile(r"label\s*=\s*['\"]right['\"]")
GLOBAL_STAT = re.compile(r"\.(mean|std|max|min|median|quantile|rank)\(\s*\)")
WINDOWED = re.compile(r"rolling|expanding|ewm|groupby|resample|axis\s*=")
FIT_CALL = re.compile(r"\.(fit|fit_transform)\(")


def _lines(src: str) -> list[tuple[int, str]]:
    return [(i + 1, l) for i, l in enumerate(src.splitlines())
            if l.strip() and not l.strip().startswith("#")]


def _q(n: int, line: str) -> str:
    return f"L{n}: {line.strip()}"


def scan_repainting(src: str) -> list[tuple[str, str]]:
    hits = []
    for n, line in _lines(src):
        code = line.split("#", 1)[0]
        for pat, why in REPAINT_PATTERNS:
            if re.search(pat, code):
                hits.append((_q(n, line), why))
        if RESAMPLE.search(code) and not RESAMPLE_OK.search(code):
            hits.append((_q(n, line), "resample without label='right': bar is stamped at its OPEN but contains data to its close"))
        if GLOBAL_STAT.search(code) and not WINDOWED.search(code):
            hits.append((_q(n, line), "whole-series statistic: normalizing with it leaks the future mean/std"))
        if FIT_CALL.search(code):
            hits.append((_q(n, line), "model/scaler fit: verify it sees training data only"))
    return hits


_HARD = {"negative shift reads future bars", "centered window uses future bars",
         "back-fill copies future values into the past", "zigzag repaints its last leg",
         "two-sided smoother/interpolation", "as-of join pulling forward/nearest rows",
         "positional index ahead of the current bar", "'same' convolution is centered",
         "peak detection confirms with bars after the peak"}


# --------------------------------------------------------------------------
# dynamic look-ahead probe
# --------------------------------------------------------------------------
def perturbation_probe(prices: pd.Series, signal_fn: Callable[[pd.Series], pd.Series],
                       n_points: int = 8, seed: int = 0, warmup: int = 0) -> dict:
    """Replace everything after t with a different random path and recompute.

    A causal signal is bit-for-bit unchanged on [0, t]. Anything that reads
    the future — negative shifts, centered windows, global normalization,
    repainting pivots, a scaler fit on all data — changes. This catches leaks
    no regex can see.
    """
    rng = np.random.default_rng(seed)
    base = signal_fn(prices).astype(float)
    n = len(prices)
    lo = max(warmup + 5, n // 4)
    points = np.unique(np.linspace(lo, n - 5, n_points).astype(int))
    log_r = np.log(prices).diff().dropna()
    vol = float(log_r.std()) or 0.01
    failures = []
    for t in points:
        fake = prices.copy()
        tail = n - t - 1
        shocks = rng.normal(0, vol, tail) * rng.choice([-3.0, 3.0])  # make it very different
        fake.iloc[t + 1:] = prices.iloc[t] * np.exp(np.cumsum(shocks))
        pert = signal_fn(fake).astype(float)
        a, b = base.iloc[: t + 1].to_numpy(), pert.iloc[: t + 1].to_numpy()
        diff = ~np.isclose(a, b, equal_nan=True, atol=1e-9)
        if diff.any():
            first = int(np.argmax(diff))
            failures.append({"t": str(prices.index[t]), "first_changed_bar": str(prices.index[first]),
                             "n_changed": int(diff.sum())})
    return {"points_tested": len(points), "failures": failures}


# --------------------------------------------------------------------------
# regime split
# --------------------------------------------------------------------------
def regimes(prices: pd.Series, ma: int = 200) -> pd.Series:
    sma = prices.rolling(ma).mean()
    slope = sma.diff(max(ma // 10, 1))
    lab = pd.Series("chop", index=prices.index)
    lab[(prices > sma) & (slope > 0)] = "bull"
    lab[(prices < sma) & (slope < 0)] = "bear"
    lab[sma.isna()] = "warmup"
    return lab


def regime_report(prices: pd.Series, net: pd.Series, cfg: Config, ma: int = 200) -> dict:
    lab = regimes(prices, ma).reindex(net.index)
    out = {}
    for name in ["bull", "bear", "chop"]:
        seg = net[lab == name]
        m = metrics(seg, cfg) if len(seg) >= 3 else {"n_obs": len(seg)}
        out[name] = {"share": round(float((lab == name).mean()), 3), "n_obs": int(len(seg)),
                     "sharpe": m.get("sharpe"), "total_return_pct": m.get("total_return_pct")}
    return out


# --------------------------------------------------------------------------
# the eight checks
# --------------------------------------------------------------------------
def _engine_line(token: str) -> str:
    src = inspect.getsource(_engine)
    for n, l in enumerate(src.splitlines(), 1):
        if token in l:
            return f"engine.py L{n}: {l.strip()}"
    return f"engine.py: {token}"


def _scan_user_backtest(src: str) -> tuple[list[str], list[str], list[str]]:
    """Return (unshifted position lines, shifted position lines, cost lines)."""
    unshifted, shifted, costs = [], [], []
    for n, l in _lines(src):
        code = l.split("#", 1)[0]
        if re.search(r"\b(pos|position|positions|holding)s?\s*=", code) and "signal" in code:
            (shifted if re.search(r"\.shift\(\s*[1-9]", code) else unshifted).append(_q(n, l))
        if re.search(r"fee|commission|slippage|spread|cost", code, re.I):
            costs.append(_q(n, l))
    return unshifted, shifted, costs


def critique(
    prices: pd.Series,
    signal: pd.Series,
    cfg: Config,
    gates: Gates,
    *,
    signal_fn: Callable[[pd.Series], pd.Series] | None = None,
    source: str | None = None,
    user_backtest_source: str | None = None,
    universe: list[dict] | None = None,
    bar_label: str | None = None,
    n_params: int | None = None,
    params_fit_out_of_sample: bool = False,
    extra_series: dict[str, pd.Series] | None = None,
    warmup: int = 0,
) -> list[Finding]:
    F: list[Finding] = []
    bt1 = backtest(prices, signal, cfg)
    m1 = metrics(bt1["net"], cfg)

    # 1. look-ahead ---------------------------------------------------------
    f = Finding(1, "look-ahead: signal shifted before becoming a position", ABSENT)
    f.evidence.append(_engine_line(".shift(cfg.execution_lag)"))
    f.evidence.append(f"execution_lag = {cfg.execution_lag}")
    if user_backtest_source:
        uns, sh, _ = _scan_user_backtest(user_backtest_source)
        f.evidence += [f"user code (unshifted): {x}" for x in uns] + [f"user code (shifted): {x}" for x in sh]
        if uns:
            f.status = PRESENT
            f.detail = "Your own backtest builds a position from an unshifted signal. This service re-runs it shifted; your numbers are not comparable."
    if signal_fn is not None:
        probe = perturbation_probe(prices, signal_fn, warmup=warmup)
        f.evidence.append(f"perturbation probe: {probe['points_tested']} cut points, {len(probe['failures'])} changed the past")
        for x in probe["failures"][:5]:
            f.evidence.append(f"  future edited after {x['t']} changed signal at {x['first_changed_bar']} ({x['n_changed']} bars)")
        if probe["failures"]:
            f.status = PRESENT
            f.detail = "The signal at t depends on data after t. The engine's shift cannot fix a signal that already contains the future."
    else:
        f.detail = "No callable signal: the future-perturbation probe could not run. A precomputed signal can embed look-ahead the shift does not remove."
        if f.status == ABSENT:
            f.status = UNKNOWN
    sr = m1.get("sharpe", 0.0)
    if abs(sr) >= gates.implausible_sharpe_fail:
        f.status = PRESENT if f.status != PRESENT else f.status
        f.evidence.append(f"Sharpe {sr} >= {gates.implausible_sharpe_fail}: treated as leakage until proven otherwise")
    elif abs(sr) >= gates.implausible_sharpe_warn:
        f.evidence.append(f"Sharpe {sr} >= {gates.implausible_sharpe_warn}: implausible, inspect manually")
        if f.status == ABSENT:
            f.status = WARN
    F.append(f)

    # 2. survivorship -------------------------------------------------------
    f = Finding(2, "survivorship: delisted assets in the universe", UNKNOWN)
    if universe:
        delisted = [u for u in universe if u.get("delisted")]
        f.evidence.append(f"universe size {len(universe)}, delisted {len(delisted)}")
        f.evidence += [f"delisted: {u['symbol']} @ {u['delisted']}" for u in delisted[:10]]
        span_years = (prices.index[-1] - prices.index[0]).days / 365
        if len(universe) == 1:
            f.status = UNKNOWN
            f.detail = "Single asset. You picked it knowing it survived; that choice is survivorship the data cannot show."
        elif not delisted and span_years > 1:
            f.status = PRESENT
            f.detail = f"{span_years:.1f} years of crypto with zero delistings is not a real universe."
        else:
            f.status = ABSENT
    else:
        f.detail = "No universe metadata supplied ({symbol, listed, delisted}). Not checkable."
    F.append(f)

    # 3. repainting ---------------------------------------------------------
    f = Finding(3, "repainting: indicators using future data", UNKNOWN)
    if source:
        hits = scan_repainting(source)
        hard = [h for h in hits if h[1] in _HARD]
        f.evidence += [f"{q}  <- {why}" for q, why in hits]
        if hard:
            f.status = PRESENT
        elif hits:
            f.status = WARN
        else:
            f.status = ABSENT
            f.evidence.append("static scan: no repainting constructs found")
    else:
        f.detail = "No source supplied for static scan."
    if F[0].status == PRESENT and any("perturbation" in e for e in F[0].evidence) and f.status != PRESENT:
        f.status = PRESENT
        f.detail = "Static scan missed it but the perturbation probe proved future dependence."
    F.append(f)

    # 4. costs --------------------------------------------------------------
    f = Finding(4, "costs: fees AND slippage on turnover", ABSENT)
    f.evidence.append(_engine_line("costs = turnover *"))
    f.evidence.append(f"fee_bps={cfg.fee_bps} slippage_bps={cfg.slippage_bps} per side")
    if cfg.fee_bps <= 0 or cfg.slippage_bps <= 0:
        f.status = PRESENT
        f.detail = "Zero fee or zero slippage configured."
    cfg2 = Config(**{**cfg.to_dict(), "fee_bps": cfg.fee_bps * 2, "slippage_bps": cfg.slippage_bps * 2})
    m2 = metrics(backtest(prices, signal, cfg2)["net"], cfg2)
    ann_turn = float(bt1["turnover"].mean() * m1.get("periods_per_year", 365))
    f.evidence.append(f"Sharpe at 1x costs {m1.get('sharpe')}, at 2x costs {m2.get('sharpe')}; annual turnover {ann_turn:.1f}x")
    if m1.get("sharpe", 0) > 0 and m2.get("sharpe", 0) <= 0:
        f.status = WARN if f.status == ABSENT else f.status
        f.detail = "Edge does not survive doubled costs. Real crypto costs routinely double in volatile bars."
    if user_backtest_source:
        _, _, cl = _scan_user_backtest(user_backtest_source)
        f.evidence += [f"user code: {x}" for x in cl] or ["user code: no fee/slippage line found"]
    F.append(f)

    # 5. fill assumption ----------------------------------------------------
    f = Finding(5, "fill: execution at a price never available", ABSENT)
    f.evidence.append("fills modeled at the close of bar t-lag plus slippage_bps; no high/low/intrabar fills")
    cfgl = Config(**{**cfg.to_dict(), "execution_lag": cfg.execution_lag + 1})
    ml = metrics(backtest(prices, signal, cfgl)["net"], cfgl)
    s1, s2 = m1.get("sharpe", 0.0), ml.get("sharpe", 0.0)
    f.evidence.append(f"Sharpe at lag {cfg.execution_lag}: {s1}; at lag {cfgl.execution_lag}: {s2}")
    if s1 > 0.5 and s2 < s1 * gates.lag2_retained_min:
        f.status = WARN
        f.detail = ("Edge collapses with one extra bar of delay: it lives in the fill bar. Either you need "
                    "sub-bar execution you have not modeled, or the signal sees that bar.")
    F.append(f)

    # 6. parameter fitting --------------------------------------------------
    f = Finding(6, "parameter fitting on the whole dataset", PRESENT)
    f.evidence.append(f"free parameters: {n_params if n_params is not None else 'undeclared'}")
    if params_fit_out_of_sample:
        f.status = ABSENT
        f.evidence.append("parameters refit on each walk-forward train window; scored only out of sample")
    else:
        f.detail = "Parameters were chosen with the test period visible. Only the deflated Sharpe and walk-forward can discount that."
    F.append(f)

    # 7. sample regimes -----------------------------------------------------
    f = Finding(7, "sample lacks both bull and bear regimes", ABSENT)
    rr = regime_report(prices, bt1["net"], cfg)
    for k, v in rr.items():
        f.evidence.append(f"{k}: share {v['share']}, n {v['n_obs']}, Sharpe {v['sharpe']}, return {v['total_return_pct']}%")
    rolling_peak = prices.cummax()
    worst_dd = float((prices / rolling_peak - 1).min())
    f.evidence.append(f"underlying max drawdown {worst_dd*100:.1f}%")
    if rr["bull"]["share"] < 0.1 or rr["bear"]["share"] < 0.1 or worst_dd > -0.2:
        f.status = PRESENT
        f.detail = "Need >=10% of bars in each of bull and bear, and an underlying drawdown of at least 20%."
    else:
        pos = [k for k in ("bull", "bear", "chop") if (rr[k]["sharpe"] or 0) > 0 and rr[k]["n_obs"] > 30]
        if len(pos) == 1:
            f.status = WARN
            f.detail = f"Edge exists only in the {pos[0]} regime. It is a regime bet, not a strategy."
    F.append(f)

    # 8. data alignment -----------------------------------------------------
    f = Finding(8, "data alignment: timezone and bar-close convention", ABSENT)
    idx = prices.index
    tz = str(idx.tz) if idx.tz is not None else None
    f.evidence.append(f"prices tz={tz}, bars={len(idx)}, bar_label={bar_label}")
    if tz is None:
        f.status = UNKNOWN
        f.detail = "Naive timestamps. Declare UTC explicitly."
    if bar_label is None:
        f.status = UNKNOWN if f.status != PRESENT else f.status
        f.detail += " bar_label undeclared: Binance-style klines are stamped at OPEN; joining them to anything else leaks one bar."
    elif bar_label == "open":
        f.status = PRESENT
        f.detail += " Close prices stamped at bar open: every timestamp is one bar early."
    steps = pd.Series(idx).diff().dropna()
    med = steps.median()
    gaps = steps[steps > med * 1.5]
    if len(gaps):
        f.evidence.append(f"{len(gaps)} gaps > 1.5x median spacing ({med}); largest {gaps.max()}")
        if f.status == ABSENT:
            f.status = WARN
    for name, s in (extra_series or {}).items():
        stz = str(s.index.tz) if getattr(s.index, "tz", None) is not None else None
        f.evidence.append(f"{name}: tz={stz}, overlap {len(s.index.intersection(idx))}/{len(idx)}")
        if stz != tz:
            f.status = PRESENT
            f.detail += f" {name} timezone differs from prices."
    F.append(f)
    return F


LLM_CRITIC_PROMPT = """Review this backtest for the following errors. For each one,
state PRESENT or ABSENT and quote the line.
1. Look-ahead: is the signal shifted before becoming a position?
2. Survivorship: does the asset list include delisted tickers?
3. Repainting: does any indicator use future data (centered
   moving averages, zigzag, unshifted resample)?
4. Costs: are fees AND slippage applied on turnover?
5. Fill assumption: does it assume execution at a price that
   was never actually available?
6. Parameter fitting: how many parameters, and were they
   chosen by looking at the whole dataset?
7. Sample: does the test period contain both a bull and a
   bear regime?
8. Data alignment: are all series on the same timezone and
   bar-close convention?
Do not summarize. Quote lines.
"""
