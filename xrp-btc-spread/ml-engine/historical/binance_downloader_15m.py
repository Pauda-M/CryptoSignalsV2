import os
import time
import requests
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing in .env")

BINANCE_URL = "https://api.binance.com/api/v3/klines"

ASSETS = ["BTCUSDT", "XRPUSDT", "ETHUSDT", "XLMUSDT", "LINKUSDT"]
INTERVAL = "15m"
BATCH = 500


def ts(ms):
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def db():
    return psycopg2.connect(DATABASE_URL)


def fetch_klines(symbol, interval, start_ts, end_ts):
    out = []
    limit = 1000
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    t = start_ts
    while True:
        params["startTime"] = int(t.timestamp() * 1000)

        r = requests.get(BINANCE_URL, params=params, timeout=10)
        if r.status_code != 200:
            time.sleep(1)
            continue

        data = r.json()
        if not data:
            break

        for k in data:
            if len(k) < 11:
                continue  # SKIP malformed rows
            open_dt = ts(k[0])
            if open_dt > end_ts:
                return out
            out.append(k)

        if len(data) < limit:
            break

        t = ts(data[-1][0]) + timedelta(minutes=15)
        time.sleep(0.25)

    return out


def build_tuple(symbol, k):
    """Build a correct 15-field tuple, or return None if invalid."""
    try:
        return (
            "binance",              # exchange
            symbol,
            INTERVAL,
            ts(k[0]),               # open_time
            ts(k[6]),               # close_time
            float(k[1]),            # open
            float(k[2]),            # high
            float(k[3]),            # low
            float(k[4]),            # close
            float(k[5]),            # volume
            float(k[7]),            # quote_volume
            int(k[8]),              # trades_count
            float(k[9]),            # taker_buy_base_volume
            float(k[10]),           # taker_buy_quote_volume
            True
        )
    except Exception:
        return None  # SKIP malformed rows safely


def insert_batch(cur, symbol, batch):
    sql = """
        INSERT INTO market_candles(
            exchange, symbol, interval,
            open_time, close_time,
            open, high, low, close,
            volume, quote_volume,
            trades_count,
            taker_buy_base_volume,
            taker_buy_quote_volume,
            is_closed
        )
        VALUES %s
        ON CONFLICT ON CONSTRAINT ux_market_candles_uniq
        DO UPDATE SET
            close_time = EXCLUDED.close_time,
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            quote_volume = EXCLUDED.quote_volume,
            trades_count = EXCLUDED.trades_count,
            taker_buy_base_volume = EXCLUDED.taker_buy_base_volume,
            taker_buy_quote_volume = EXCLUDED.taker_buy_quote_volume,
            is_closed = TRUE;
    """

    execute_batch(cur, sql, batch, page_size=BATCH)


def main():
    print("=== Binance 15m Downloader ===")

    conn = db()
    cur = conn.cursor()

    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=365 * 4)

    for asset in ASSETS:
        print(f"\n=== {asset} ===")
        data = fetch_klines(asset, INTERVAL, start_date, end_date)
        print(f"[OK] fetched {len(data)} rows")

        batch = []
        for k in data:
            tup = build_tuple(asset, k)
            if tup is None:
                continue  # SKIP invalid row
            batch.append(tup)

            if len(batch) >= BATCH:
                insert_batch(cur, asset, batch)
                conn.commit()
                batch = []

        if batch:
            insert_batch(cur, asset, batch)
            conn.commit()

        print(f"[OK] {asset} inserted")

    cur.close()
    conn.close()
    print("\n✔ DONE — All assets imported.")


if __name__ == "__main__":
    main()
