import psycopg2
import requests
import sys
import time
from datetime import datetime, timedelta, timezone
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
BASE_URL = "https://api.binance.com/api/v3/klines"
INTERVAL = "15m"
LIMIT = 1000            # Binance maximum
SLEEP = 0.25            # Keep below rate limits
EXCHANGE = "BINANCE"


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def ms_to_ts(ms: int):
    """Binance ms → Python datetime with timezone (PostgreSQL safe)."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def get_last_time(cur, symbol):
    """Return the most recent candle timestamp."""
    cur.execute("""
        SELECT open_time
        FROM market_candles
        WHERE symbol=%s AND interval=%s
        ORDER BY open_time DESC
        LIMIT 1
    """, (symbol, INTERVAL))

    row = cur.fetchone()
    return row[0] if row else None


def fetch_binance(symbol, start_time):
    """Fetch candles from Binance API."""
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": LIMIT,
    }

    if start_time:
        params["startTime"] = int(start_time.timestamp() * 1000)

    r = requests.get(BASE_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def insert_batch(cur, rows):
    """Insert batch into PostgreSQL — bulletproof format."""
    sql = """
        INSERT INTO market_candles (
            exchange,
            symbol,
            interval,
            open_time,
            close_time,
            open,
            high,
            low,
            close,
            volume,
            quote_volume,
            trades_count,
            taker_buy_base_volume,
            taker_buy_quote_volume,
            is_closed
        )
        VALUES %s
        ON CONFLICT (exchange, symbol, interval, open_time)
        DO NOTHING;
    """

    execute_values(cur, sql, rows, page_size=500)


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python downloader_15m.py BTCUSDT")
        sys.exit(1)

    symbol = sys.argv[1].upper()

    print(f"\n=== {symbol} — 15m Historical Downloader ===")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Resume logic
    last_time = get_last_time(cur, symbol)

    if last_time:
        print(f"[INFO] Resuming from last stored: {last_time}")
        start = last_time + timedelta(minutes=15)
    else:
        print("[INFO] No history found → full download")
        start = None

    total_inserted = 0

    while True:
        data = fetch_binance(symbol, start)

        if not data:
            print("[INFO] No more candles available.")
            break

        rows = []

        for d in data:
            open_time = ms_to_ts(d[0])
            close_time = ms_to_ts(d[6])

            rows.append((
                EXCHANGE,
                symbol,
                INTERVAL,
                open_time,
                close_time,
                float(d[1]),    # open
                float(d[2]),    # high
                float(d[3]),    # low
                float(d[4]),    # close
                float(d[5]),    # volume
                float(d[7]),    # quote_volume
                int(d[8]),      # trade count
                float(d[9]),    # taker buy base
                float(d[10]),   # taker buy quote
                True            # closed candle
            ))

        insert_batch(cur, rows)
        conn.commit()

        total_inserted += len(rows)
        print("FUCK OFF i inserted "{len(rows)} rows (total: {total_inserted}))

        # Advance window
        last_close = ms_to_ts(data[-1][6])
        start = last_close + timedelta(milliseconds=1)

        time.sleep(SLEEP)

        if len(data) < LIMIT:
            break

    cur.close()
    conn.close()

    print ("FUCK OFF i inserted "{len(rows)} candles (total: {total_inserted}))


if __name__ == "__main__":
    main()
