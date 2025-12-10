import psycopg2
import requests
from datetime import datetime, timedelta, timezone
import time
import os
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
ASSET = "BTCUSDT"
INTERVAL = "15m"
EXCHANGE = "BINANCE"
LIMIT = 1000  # Binance max

BASE_URL = "https://api.binance.com/api/v3/klines"

# ------------------------------------------------------------------------------------
# Convert Binance ms timestamps → TIMESTAMPTZ
# ------------------------------------------------------------------------------------
def ms_to_ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

# ------------------------------------------------------------------------------------
# Get last stored timestamp
# ------------------------------------------------------------------------------------
def get_last_time(cur):
    cur.execute("""
        SELECT open_time 
        FROM market_candles 
        WHERE symbol=%s AND interval=%s 
        ORDER BY open_time DESC LIMIT 1
    """, (ASSET, INTERVAL))

    row = cur.fetchone()
    return row[0] if row else None

# ------------------------------------------------------------------------------------
# Fetch klines from Binance
# ------------------------------------------------------------------------------------
def fetch_binance(symbol, interval, start_time):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": LIMIT
    }
    if start_time is not None:
        params["startTime"] = int(start_time.timestamp() * 1000)

    r = requests.get(BASE_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# ------------------------------------------------------------------------------------
# Insert batch into database safely
# ------------------------------------------------------------------------------------
def insert_batch(cur, batch):
    sql = """
        INSERT INTO market_candles (
            exchange, symbol, interval, open_time, close_time,
            open, high, low, close,
            volume, quote_volume, trades_count,
            taker_buy_base_volume, taker_buy_quote_volume,
            is_closed
        )
        VALUES %s
        ON CONFLICT (exchange, symbol, interval, open_time)
        DO NOTHING;
    """

    execute_values(cur, sql, batch, page_size=500)

# ------------------------------------------------------------------------------------
# Main execution
# ------------------------------------------------------------------------------------
def main():
    print(f"\n=== {ASSET} — 15m Downloader ===")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    last_time = get_last_time(cur)

    if last_time is None:
        print("[INFO] No existing data → downloading ALL history")
        start_time = None
    else:
        print(f"[INFO] Resuming from {last_time}")
        start_time = last_time + timedelta(minutes=15)

    total_inserted = 0

    while True:
        data = fetch_binance(ASSET, INTERVAL, start_time)

        if not data:
            break

        batch = []
        for d in data:
            open_t = ms_to_ts(d[0])
            close_t = ms_to_ts(d[6])

            batch.append((
                EXCHANGE,
                ASSET,
                INTERVAL,
                open_t,
                close_t,
                float(d[1]),  # open
                float(d[2]),  # high
                float(d[3]),  # low
                float(d[4]),  # close
                float(d[5]),  # volume
                float(d[7]),  # quote_volume
                int(d[8]),    # trades_count
                float(d[9]),  # taker_buy_base_volume
                float(d[10]), # taker_buy_quote_volume
                True          # is_closed always TRUE
            ))

        insert_batch(cur, batch)
        conn.commit()

        total_inserted += len(batch)
        print(f"[OK] Inserted {len(batch)} rows (running total {total_inserted})")

        # Prepare next batch start_time
        last_close = ms_to_ts(data[-1][6])
        start_time = last_close + timedelta(milliseconds=1)

        # Binance rate limit safety
        time.sleep(0.25)

        if len(data) < LIMIT:
            break

    cur.close()
    conn.close()
    print(f"\n🎉 DONE — Inserted {total_inserted} candles for {ASSET}\n")


if __name__ == "__main__":
    main()
