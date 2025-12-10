import psycopg2
import sys
import time
import requests
from psycopg2.extras import execute_values
from datetime import datetime, timezone, timedelta

# --------------------------------------------------------
# 🔥 EXACT SAME DB CONNECT STYLE YOU ALREADY USE
# --------------------------------------------------------
from dotenv import load_dotenv
import os
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# --------------------------------------------------------
# Binance API constants
# --------------------------------------------------------
LIMIT = 1000
INTERVAL = "15m"
BASE_URL = "https://api.binance.com/api/v3/klines"

# --------------------------------------------------------
# Helpers
# --------------------------------------------------------
def ms_to_ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

def fetch_binance(symbol, start_ms):
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "startTime": start_ms,
        "limit": LIMIT
    }
    r = requests.get(BASE_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# --------------------------------------------------------
# Duplicate-safe insert
# --------------------------------------------------------
def insert_batch(symbol, rows):
    sql = """
        INSERT INTO market_candles(
            exchange, symbol, interval, open_time, close_time,
            open, high, low, close, volume, quote_volume,
            trades_count, taker_buy_base_volume, taker_buy_quote_volume,
            is_closed
        )
        VALUES %s
        ON CONFLICT ON CONSTRAINT ux_market_candles_uniq DO NOTHING;
    """

    batch = []
    for c in rows:
        batch.append((
            "BINANCE",
            symbol,
            INTERVAL,
            ms_to_ts(c[0]),
            ms_to_ts(c[6]),
            float(c[1]),   # open
            float(c[2]),   # high
            float(c[3]),   # low
            float(c[4]),   # close
            float(c[5]),   # volume
            float(c[7]),   # quote_volume
            int(c[8]),     # trade count
            float(c[9]),   # taker_buy_base
            float(c[10]),  # taker_buy_quote
            True
        ))

    execute_values(cur, sql, batch, page_size=500)
    conn.commit()


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python import15m_candles.py ASSET")
        sys.exit(1)

    symbol = sys.argv[1].upper()

    print(f"\n=== Importing {symbol} (15m) ===")

    # Find last imported timestamp
    cur.execute("""
        SELECT EXTRACT(EPOCH FROM MAX(open_time))*1000
        FROM market_candles
        WHERE symbol=%s AND interval=%s
    """, (symbol, INTERVAL))

    last_val = cur.fetchone()[0]

    if last_val is None:
        # You said you already have 4y XRP-BTC data, so let's start in 2019
        start_ms = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        print("[INFO] No previous data → starting from 2019-01-01")
    else:
        start_ms = int(last_val)
        print(f"[INFO] Resuming from: {ms_to_ts(start_ms)}")

    total = 0

    while True:
        data = fetch_binance(symbol, start_ms)

        if not data:
            print("[DONE] No more data.")
            break

        insert_batch(symbol, data)
        total += len(data)

        print(f"[OK] Inserted {len(data)} rows (total {total})")

        # move to next window
        start_ms = data[-1][6] + 1
        time.sleep(0.2)

        if len(data) < LIMIT:
            break

    print(f"\n✔ FINISHED: Inserted total {total} rows for {symbol}\n")


if __name__ == "__main__":
    main()
