"""Copy ChromeOmega trade-log rows INTO btval's own store. Read-only on the source.

The source DSN is passed by the operator at run time (env BTVAL_SOURCE_DSN or
--source-dsn) and is never stored. The session is opened READ ONLY, so even a
DSN with write rights cannot write through this module. api_key_ref and
user_id are never selected: btval has no business holding key material.
"""
from __future__ import annotations

from .store import Store

SOURCE_TABLES = {
    "live": '"CryptoTraders"."ChromeOmega_live_trade_log"',
    "sim": '"CryptoTraders"."ChromeOmega_sim_trade_log"',
}
# Selected explicitly. signal_price exists on the live log only.
BASE_COLS = ["id", "session_id", "position_id", "position_group_id", "strategy_id", "strategy_name",
             "symbol", "direction", "entry_price", "exit_price", "size_usd", "notional_usd", "leverage",
             "pnl_usd", "fee_usd", "funding_usd", "exit_reason", "exit_is_maker", "signal_score",
             "signal_bucket_ts", "opened_at", "closed_at"]


def build_query(table: str, has_signal_price: bool) -> str:
    if table not in SOURCE_TABLES:
        raise ValueError(f"table must be one of {list(SOURCE_TABLES)}")
    cols = BASE_COLS + (["signal_price"] if has_signal_price else [])
    sel = ", ".join(f"{c}::text AS {c}" if c == "position_group_id" else c for c in cols)
    return f"SELECT {sel} FROM {SOURCE_TABLES[table]} WHERE id > %s ORDER BY id LIMIT %s"


def sync(store: Store, source_dsn: str, table: str, venue: str, source_db: str,
         batch: int = 5000) -> dict:
    import psycopg  # optional dependency; only the operator running sync needs it

    since = store.max_source_row_id(venue, source_db)
    total = {"received": 0, "inserted": 0, "duplicates": 0, "from_id": since}
    with psycopg.connect(source_dsn, autocommit=False) as cx:
        cx.execute("SET TRANSACTION READ ONLY")
        has_sig = cx.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='CryptoTraders' "
            "AND table_name=%s AND column_name='signal_price'",
            (SOURCE_TABLES[table].split('.')[1].strip('"'),)).fetchone() is not None
        q = build_query(table, has_sig)
        while True:
            cur = cx.execute(q, (since, batch))
            names = [d.name for d in cur.description]
            rows = [dict(zip(names, r)) for r in cur.fetchall()]
            if not rows:
                break
            for r in rows:
                r["source_row_id"] = r.pop("id")
                for k, v in list(r.items()):
                    if hasattr(v, "is_finite"):  # Decimal -> float
                        r[k] = float(v)
            res = store.upsert_fills(rows, venue=venue, source_db=source_db)
            for k in ("received", "inserted", "duplicates"):
                total[k] += res.get(k, 0)
            since = rows[-1]["source_row_id"]
            if len(rows) < batch:
                break
        cx.rollback()
    total["to_id"] = since
    total["signal_price_available"] = has_sig
    return total
