# backtest-validator (`btval`)

A standalone service that tries to reject trading strategies, then paper-trades
the survivors on **pbFinance** (the Binance-compatible simulator) with costs
measured from real fills, and shows it all on a live dashboard.

It imports nothing from the rest of this repository, keeps its **own database**
(SQLite, or its own `btval-db` Postgres), and can place orders **only** on the
simulator.

```
validate ──► DEPLOYABLE run (+ kill conditions)
                 │
real fills ──► sync (read-only) ──► calibrate ──► slippage / fee bps
                 │                                     │
                 └───────────► paper session ◄─────────┘
                                   │  per closed bar: signal → MARKET order on pbFinance
                                   │  → booked at sim fill moved by measured slippage + fees
                                   ▼
                     btval-db  ──►  dashboard  (http://host:8790/)
```

```
DEPLOYABLE  only if all three gates pass
REJECT      otherwise, with the quoted reason
```

## The three gates

| Gate | Passes when | Implemented in |
|---|---|---|
| 1. Critic | No `PRESENT` finding on checks 1, 2, 3, 4, 5, 8 | `critic.py` |
| 2. Deflated Sharpe | DSR > 0.95 with every trial counted | `stats.py` |
| 3. Walk-forward | ≥60% positive folds, worst fold no worse than noise's worst, stitched OOS Sharpe > 0, sample has bull **and** bear | `walkforward.py`, `pipeline.py` |

A `DEPLOYABLE` report includes `kill_conditions`. These are computed from the
**out-of-sample** statistics, not the in-sample ones, and you fix them before
deploying. `/monitor` checks live returns against them.

## The eight critic checks: code, not an LLM's opinion

Each check reports `PRESENT` (the error is there), `ABSENT`, `UNKNOWN` (can't
be checked from what was supplied; this is **not** a pass) or `WARN`. Evidence
is quoted source lines (`L12: ...`) or measured numbers.

1. **Look-ahead.** The engine enforces `signal.shift(execution_lag)`; lag 0 is refused. A
   **future-perturbation probe** rewrites every bar after *t* with a different
   random path and recomputes the signal. A causal signal stays bit-identical up to *t*.
   This catches negative shifts, centered windows, whole-series z-scores, repainting
   pivots and scalers fit on all the data, including leaks no regex can see. Sharpe ≥ 3
   counts as `PRESENT`; Sharpe ≥ 2 is a `WARN`.
2. **Survivorship.** Uses the `universe` metadata (`{symbol, listed, delisted}`). A
   multi-year universe with zero delistings counts as `PRESENT`. A single asset is `UNKNOWN`,
   because you picked it knowing it survived.
3. **Repainting.** A static scan for `shift(-n)`, `center=True`, bfill, zigzag,
   `filtfilt`/`savgol`, forward `merge_asof`, `resample` without `label='right'`,
   whole-series `.mean()/.std()` and `.fit(`. The probe from check 1 overrides a clean scan.
4. **Costs.** Fee and slippage per side, charged on turnover, including the
   initial entry. The check re-runs the backtest at 2× costs.
5. **Fill.** Re-runs at `execution_lag + 1`. If the edge dies, it lives in the fill bar.
6. **Parameter fitting.** Counts the parameters and records whether selection was out of sample.
7. **Regimes.** Uses a 200-bar SMA plus its slope. Needs ≥10% of bars in bull and in bear,
   and an underlying drawdown of at least 20%. Reports Sharpe for each regime.
8. **Alignment.** Checks timezone, gaps, and `bar_label`. Exchange klines are usually stamped
   at **open**; the service re-stamps them to close time.

The LLM prompt is still available at `GET /critic/prompt` if you want a second
opinion. It is advisory and does not affect any gate.

## Usage

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m btval demo                       # random walk -> REJECT
python -m btval validate --csv BTCUSDT_1d.csv --bar-label open \
       --strategy tsmom --prior-trials 12  # exit code 0 = DEPLOYABLE, 2 = REJECT
python -m btval serve --port 8790          # dashboard at http://localhost:8790/
cp .env.example .env && docker compose up -d --build   # btval-db + api + paper runner
```

`--prior-trials` is required on purpose. Count every variation you ran on this
data before this run.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/strategies`, `/critic/prompt` | |
| POST | `/validate/strategy` | Full validation of a registry strategy (probe, refit walk-forward, DSR) |
| POST | `/validate/signal` | A precomputed signal. Weaker: no probe, no refit. Gate 3 **requires** `holdout_start` |
| POST | `/stats/deflated-sharpe` | Per-period SR, number of trials, number of observations |
| POST | `/size` | Fixed-fractional sizing including costs, plus a losing-streak table |
| POST | `/monitor` | Live returns plus `kill_conditions` → `CONTINUE` / `HALT` |

### Adding a strategy

Add a module under `btval/strategies/` that exports `STRATEGY = Strategy(name,
signal_fn, grid, warmup, mechanism)`, and register its name in `_BUILTIN`. Or pass a
dotted module path. `signal_fn(prices, **params)` must be causal; the probe checks this.

## Execution reality: real fills, paper trading, dashboard

### Own database, never the trading one
`BTVAL_DB_URL` defaults to `sqlite:///./btval.db`. In `docker-compose.yml` it points
at `btval-db`, a dedicated Postgres instance that isn't published on any port. `Store` refuses
known trading targets (`192.168.50.88:{5432,15432,15442,25432}`, and databases
named pbTradeNet, pbMasterData, pbquant, pb_mldata, pbCICDStage). A pasted production DSN therefore fails
loudly instead of creating tables in production.

### Real fills → measured costs
```bash
# read-only copy of ChromeOmega's trade log into btval-db. The DSN is used once and never stored.
BTVAL_SOURCE_DSN=postgresql://pbservice:...@192.168.50.88:15442/pbTradeNet \
  python -m btval sync --table live --venue binance --source-db tradenet-prod
python -m btval calibrate --venue binance     # -> calibration_id + slippage/fee bps
```
`sync` opens a `READ ONLY` transaction, selects an explicit column list, and never
reads `api_key_ref` or `user_id`. `venue` is your declaration: the log cannot tell
pbFinance fills from Binance fills, and `ChromeOmega_sim_trade_log` is empty in
both preprod and prod.

| Endpoint | What it tells you |
|---|---|
| `POST /fills/calibrate` | Entry slippage (fill vs `signal_price`), fees, funding, signal→fill delay. Sends `recommended_config` to validation via `calibration_id`. |
| `POST /fills/shortfall` | The ideal signal→exit edge versus what the account kept: entry slippage, fees, funding, and the residual. |
| `POST /fills/venue-gap?a=pbfinance&b=binance` | The same signals on two venues: whether pbFinance agrees with Binance on *whether* a fill happened and *at what price*. |

Calibration caveats (also returned by the endpoint):
- Only **filled** orders are in a trade log. Limit entries that never filled are invisible, so the measured entry slippage understates the cost.
- Exit slippage can't be measured, because the log has no exit decision price.

### Paper trading on pbFinance
```bash
POST /paper/sessions {"strategy":"sma_cross","symbol":"BTCUSDT","interval":"1d",
                      "validation_run_id":12,"calibration_id":3,"cost_mode":"empirical"}
python -m btval paper-loop          # or the btval-runner container
```
On each closed bar, the runner:
1. Computes the signal on the last **closed** kline. The kline that is still forming is dropped.
2. Sizes the order to the target position.
3. Reserves the decision row. `UNIQUE(session, bar, kind)` plus a deterministic `newClientOrderId` means a restart, a crash or a second runner can never place a second order for the same bar.
4. Sends a MARKET order to pbFinance.
5. Books the fill at the simulator's price moved **adversely** by the calibrated slippage (`fixed` uses the mean; `empirical` samples the measured distribution, seeded by session and bar), plus fees per side.
6. Reconciles the venue position against btval's ledger.
7. Checks the kill conditions from the validation run. A **HALT** flattens the position (the order cap doesn't apply to it) and stops the session.

It stores both the raw simulator fill and the booked fill. `venue_drift_bps` (simulator fill
versus decision price) is the *measured* version of the backtest's fill
assumption. If pbFinance already models slippage, use `cost_mode: "none"` to avoid
counting slippage twice.

Guards:
- **Simulator only.** No live mode exists. The host must be in `BTVAL_SIM_HOSTS` **and** internal, and any `*binance*.*` host is refused.
- **Validation required.** A session needs a DEPLOYABLE run **for that same strategy**. Without one it needs `allow_unvalidated`, and is then labelled unvalidated permanently.
- **Rebalance band.** The default 5% band stops the runner from paying fees every bar to re-size the position to drifting equity, a cost the backtest never charges.

### Dashboard
`GET /` on the API (port 8790). It shows:
- sessions with status, staleness, ledger/venue divergence and unvalidated alerts
- equity, and drawdown against the kill limit
- fill drift per order and an execution-reality summary
- orders, validation runs and calibrations

It reads only btval-db and never calls pbFinance, so opening it can't trigger trading. It
refreshes every 30s and supports dark and light themes.

## Where this departs from the source article, and why

These are bugs in the article's code. Each one changes the verdict.

- **DSR fed an annualized Sharpe.** The z-score uses `sqrt(n_obs - 1)`, so
  the Sharpe must be per period. An annualized input is inflated by √365, and
  almost anything passes (see `test_annualized_input_would_have_passed`). The
  expected maximum must also be scaled by the dispersion of the trial Sharpes; the
  article omits it. With `n_trials=1` the article's formula returns −∞.
- **`position * log_return`** is wrong for shorts and leverage. The engine uses simple returns.
- **`turnover.fillna(0)`** gives away the cost of the initial entry. The article's "round-trip" fee
  label applied per unit of turnover is also ambiguous. Here the fee is per side.
- **Walk-forward with `test_days=60` and `metrics` requiring 100 observations** returns zero
  valid folds and raises a `KeyError`. Computing indicators on the test slice alone
  zeroes the first `warmup` bars of every fold. Here the folds use preceding history
  and are stitched into one backtest, so the carry and switching costs at fold boundaries are real.
- **"Judge on worst fold" with a fixed threshold.** A 90-day fold's annualized
  Sharpe has a standard error of about 2. Across 50 folds, even a strategy with a true Sharpe of 1.5 has a worst
  fold near −3. A fixed floor rejects real edges, and rejects them more often as you add data.
  The default floor is noise's worst fold at a Bonferroni 5% level.
- **`health_check` measured drawdown from the first return**, not from starting capital, so a loss on day one was never counted as drawdown.
- **`health_check` on a 30-bar window** fires on noise: a 30-day annualized Sharpe has a standard error of about 3.5.
  Here the window has a floor (90 bars), and decay is a one-sided PSR test.
- **`periods_per_year=365`** on 4H bars understates volatility by √6. Here the bar spacing is inferred.

## Power: what to expect

Measured on synthetic data with a planted edge (true annualized Sharpe ≈ 1.5) and
pure noise:

| Bars | Real edge passes | Noise passes |
|---|---|---|
| 1,825 (5y daily) | ~1 in 4 | 0 |
| 5,000 | 9 in 10 | 0 in 10 |

Five years of daily bars cannot reliably confirm a Sharpe-1.5 strategy. Use
finer bars or more assets rather than loosening the gates.
