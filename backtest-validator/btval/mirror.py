"""Mirror live 1m bars from pbMasterData into pbFinance's OWN database.

pbFinance reads prices from a local `hf_ohlcv_1m` table and polls it in a
tight loop with NOW()-relative filters. Pointing it at pbMasterData directly
(or through postgres_fdw, which does not push NOW() down) would scan prod's
1m table continuously. This copies only the last few minutes every pass:
read-only on the source, writes only to the target, which must not be a
trading database.
"""
from __future__ import annotations

import time

from .store import assert_not_trading_db

DDL = [
    """CREATE TABLE IF NOT EXISTS public.hf_ohlcv_1m (
        pair_id INTEGER NOT NULL, timestamp TIMESTAMPTZ NOT NULL,
        open DOUBLE PRECISION, high DOUBLE PRECISION, low DOUBLE PRECISION,
        close DOUBLE PRECISION, volume DOUBLE PRECISION,
        PRIMARY KEY (pair_id, timestamp))""",
    "CREATE TABLE IF NOT EXISTS public.hf_pairs (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL)",
]


def _sym(s: str) -> str:
    s = s.strip().upper()
    if "/" in s:
        return s
    for q in ("USDT", "BUSD", "USDC"):
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}/{q}"
    return s


def mirror_once(src, dst, minutes: int, keep_days: float) -> dict:
    with src.transaction():
        src.execute("SET TRANSACTION READ ONLY")
        pairs = src.execute("SELECT id, symbol FROM master_data.hf_pairs").fetchall()
        bars = src.execute(
            "SELECT pair_id, timestamp, open, high, low, close, volume FROM master_data.hf_ohlcv_1m "
            "WHERE timestamp > now() - make_interval(mins => %s)", (minutes,)).fetchall()
    with dst.transaction():
        for d in DDL:
            dst.execute(d)
        with dst.cursor() as cur:
            cur.executemany("INSERT INTO public.hf_pairs (id, symbol) VALUES (%s, %s) "
                            "ON CONFLICT (id) DO UPDATE SET symbol = EXCLUDED.symbol",
                            [(int(i), _sym(s)) for i, s in pairs])
            cur.executemany(
                "INSERT INTO public.hf_ohlcv_1m VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (pair_id, timestamp) DO UPDATE SET open=EXCLUDED.open, high=EXCLUDED.high, "
                "low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume", bars)
        dst.execute("DELETE FROM public.hf_ohlcv_1m WHERE timestamp < now() - make_interval(secs => %s)",
                    (keep_days * 86400,))
    return {"pairs": len(pairs), "bars": len(bars)}


def run(source_dsn: str, target_dsn: str, every: int = 10, backfill_days: float = 3.0,
        keep_days: float = 3.0, once: bool = False) -> None:
    import psycopg

    assert_not_trading_db(target_dsn.replace("postgresql://", "postgresql+psycopg://", 1))
    with psycopg.connect(source_dsn, autocommit=True) as src, psycopg.connect(target_dsn, autocommit=True) as dst:
        print({"backfill": mirror_once(src, dst, int(backfill_days * 1440), keep_days)}, flush=True)
        while not once:
            time.sleep(every)
            try:
                mirror_once(src, dst, 5, keep_days)
            except Exception as e:  # noqa: BLE001 -- keep mirroring; log and retry next pass
                print({"error": f"{type(e).__name__}: {e}"}, flush=True)
