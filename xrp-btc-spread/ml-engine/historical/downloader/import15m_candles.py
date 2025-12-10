import psycopg2
import sys
import time
from psycopg2.extras import execute_values
import requests
from datetime import datetime, timedelta, timezone

ASSET = sys.argv[1].upper()
INTERVAL = "15m"
LIMIT = 1000
BATCH_SIZE = 500

from dotenv import load_dotenv
import os
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def ms_to_ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

def get_last_close(cur, asset):
    cur.execute("""
        SELECT close_time 
        FROM market_candles
        WHERE symbol = %s AND interval = %s
        ORDER BY close_time DESC
        LIMIT 1
    """, (asset, INTERVAL))
    row = cur.fetchone()
    return row[0] if row else None

def fetch_klines(symbol, start_time):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "startTime": int(start_time.timestamp() * 1000),
        "limit": LIMIT
    }
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Binance error {resp.status_code}: {resp.text}")
    return resp.json()

def insert_batch(cur, symbol, batch):
    sql = """
        INSERT INTO market_candles (
            exchange, symbol, interval,
            open_time, close_time, open, high, low, close,
            volume, quote_volume, trades_count,
            taker_buy_base_volume, taker_buy_quote_volume,
            is_closed
        )
        VALUES (
            'binance', %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            TRUE
        )
        ON CONFLICT ( exchange, symbol, interval, open_time)
        DO NOTHING
    """
    psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)

def main():
    print(f"\n=== {ASSET} — 15m Downloader ===")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    last_close = get_last_close(cur, ASSET)
    if last_close:
        print(f"[INFO] Resuming from {last_close}")
        start_time = datetime(2017, 8, 17, tzinfo=timezone.utc)
        ##start_time = last_close + timedelta(milliseconds=1)
    else:
        print(f"[INFO] No history → downloading ALL")
        start_time = datetime(2017, 8, 17, tzinfo=timezone.utc)

    total_inserted = 0

    while True:
        klines = fetch_klines(ASSET, start_time)
        if not klines:
            break

        batch_values = []
        for k in klines:
            o, h, l, c = map(float, k[1:5])
            v = float(k[5])
            qv = float(k[7])
            t = int(k[8])
            tbv = float(k[9])
            tqbv = float(k[10])

            open_t = ms_to_ts(k[0])
            close_t = ms_to_ts(k[6])

            batch_values.append([
                ASSET, INTERVAL,
                open_t, close_t, o, h, l, c,
                v, qv, t,
                tbv, tqbv
            ])

        insert_batch(cur, ASSET, batch_values)
        conn.commit()

        total_inserted += len(batch_values)
        print(f"[OK] Inserted {len(batch_values)} rows (total {total_inserted})")

        # Move to next window
        last_close = ms_to_ts(klines[-1][6])
        start_time = last_close + timedelta(milliseconds=1)

        # Binance returns < 1000 rows near end
        if len(klines) < LIMIT:
            break

        time.sleep(0.25)

    cur.close()
    conn.close()
    print("X- DONE")

if __name__ == "__main__":
    main()
