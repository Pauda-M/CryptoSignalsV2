from __future__ import annotations

import numpy as np
import pandas as pd

TS_COLS = ("timestamp", "time", "date", "datetime", "open_time", "close_time")


def to_utc_index(values) -> pd.DatetimeIndex:
    s = pd.Series(values)
    if pd.api.types.is_numeric_dtype(s):
        unit = "ms" if s.abs().max() > 1e11 else "s"
        idx = pd.to_datetime(s, unit=unit, utc=True)
    else:
        idx = pd.to_datetime(s, utc=True)
    return pd.DatetimeIndex(idx)


def normalize_bars(prices, bar_label: str):
    """Return close prices stamped at bar CLOSE time.

    bar_label='open' (Binance/most exchange klines) is shifted forward by one
    bar so the timestamp is when the close was actually known. Accepts a
    Series or a DataFrame (so a signal column moves with its prices).
    """
    notes = []
    if bar_label not in ("open", "close"):
        raise ValueError("bar_label must be 'open' or 'close'")
    prices = prices[~prices.index.duplicated(keep="last")].sort_index()
    if bar_label == "open":
        step = pd.Series(prices.index).diff().median()
        prices = prices.copy()
        prices.index = prices.index + step
        notes.append(f"re-stamped open-time bars to close-time (+{step})")
    return prices, notes


def series_from_records(records: list[dict], value_key: str = "close") -> pd.Series:
    df = pd.DataFrame(records)
    ts = next((c for c in TS_COLS if c in df.columns), None)
    if ts is None:
        raise ValueError(f"records need one of {TS_COLS}")
    return pd.Series(df[value_key].astype(float).to_numpy(), index=to_utc_index(df[ts]), name=value_key)


def load_csv(path: str, price_col: str = "close") -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    return series_from_records(df.to_dict("records"), price_col)


def synthetic_prices(n: int = 1825, seed: int = 7, phi: float = 0.0, freq: str = "1D",
                     start: str = "2020-01-01", regime_drift: bool = True) -> pd.Series:
    """Regime-switching path (bull/bear/chop) with optional AR(1) return autocorrelation.

    regime_drift=False and phi=0 is a pure random walk: anything that 'works'
    on it is overfit. With regime_drift=True, persistent drifts are a real
    (trend) edge.
    """
    rng = np.random.default_rng(seed)
    drifts = {"bull": 0.0025, "bear": -0.0025, "chop": 0.0}
    vols = {"bull": 0.03, "bear": 0.04, "chop": 0.025}
    states = ["bull", "bear", "chop"]
    r = np.zeros(n)
    state = "bull"
    prev = 0.0
    for t in range(n):
        if rng.random() < 1 / 120:
            state = states[rng.integers(3)]
        eps = rng.normal(drifts[state] if regime_drift else 0.0, vols[state])
        prev = phi * prev + eps
        r[t] = prev
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.Series(20_000 * np.exp(np.cumsum(r)), index=idx, name="close")


_IDENT = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def load_pg_bars(dsn: str, table: str, pair_id: int, bar_label: str, since: str | None = None,
                 now: pd.Timestamp | None = None) -> tuple[pd.Series, list[str]]:
    """Closes from a NON-production Postgres OHLCV table (refuses prod hosts/DBs).

    READ ONLY transaction. Returns close prices stamped at bar CLOSE time with
    the still-forming bar dropped: real-time continuous aggregates return
    today's partial bar as if it were final.
    """
    import psycopg

    from .store import assert_not_tradenet_source
    assert_not_tradenet_source(dsn)
    if not _IDENT.match(table):
        raise ValueError("table must be schema.table")
    q = f"SELECT timestamp, close FROM {table} WHERE pair_id = %s" + (" AND timestamp >= %s" if since else "") \
        + " ORDER BY timestamp"
    with psycopg.connect(dsn) as cx:
        cx.execute("SET TRANSACTION READ ONLY")
        rows = cx.execute(q, (pair_id, since) if since else (pair_id,)).fetchall()
        cx.rollback()
    if not rows:
        raise ValueError(f"no bars for pair_id {pair_id} in {table}")
    s = pd.Series([float(r[1]) for r in rows], index=pd.DatetimeIndex([r[0] for r in rows]).tz_convert("UTC"))
    s, notes = normalize_bars(s, bar_label)
    now = now or pd.Timestamp.now(tz="UTC")
    forming = s.index > now
    if forming.any():
        notes.append(f"dropped {int(forming.sum())} still-forming bar(s) closing after {now:%Y-%m-%d %H:%M}Z")
        s = s[~forming]
    return s, notes
