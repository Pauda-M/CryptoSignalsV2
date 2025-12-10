
import os
import time
import requests
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing in .env")

SYMBOL = "XRPUSDT"
INTERVAL = "15m"
BATCH_SIZE = 500
BINANCE_URL = "https://api.binance.com/api/v3/klines"

LISTING_DATES = {
    "BTCUSDT": datetime(2017, 8, 17, tzinfo=timezone.utc),
    "ETHUSDT": datetime(2017, 8, 17, tzinfo=timezone.utc),
    "XRPUSDT": datetime(2017, 12, 30, tzinfo=timezone.utc),
    "XLMUSDT": datetime(2018, 6, 28, tzinfo=timezone.utc),
    "LINKUSDT": datetime(2019, 1, 16, tzinfo=timezone.utc),
}

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
                continue
            if ts(k[0]) > end_ts:
                return out
            out.append(k)

        if len(data) < limit:
            break

        t = ts(data[-1][0]) + timedelta(minutes=15)
        time.sleep(0.25)

    return out

def insert_batch(cur, batch):
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
        ) VALUES %s
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

    execute_values(cur, sql, batch, page_size=BATCH_SIZE)

def main():
    print(f"=== Downloading {SYMBOL} 15m ===")

    conn = db()
    cur = conn.cursor()

    start_ts = LISTING_DATES.get(SYMBOL, datetime(2019, 1, 1, tzinfo=timezone.utc))
    end_ts = datetime.now(tz=timezone.utc)

    print(f"[INFO] Fetching from {start_ts} to {end_ts}")

    data = fetch_klines(SYMBOL, INTERVAL, start_ts, end_ts)
    print(f"[INFO] Rows fetched: {len(data)}")

    batch = []
    for k in data:
        tup = (
            "binance",
            SYMBOL,
            INTERVAL,
            ts(k[0]),
            ts(k[6]),
            float(k[1]),
            float(k[2]),
            float(k[3]),
            float(k[4]),
            float(k[5]),
            float(k[7]),
            int(k[8]),
            float(k[9]),
            float(k[10]),
            True
        )
        batch.append(tup)

        if len(batch) >= BATCH_SIZE:
            insert_batch(cur, batch)
            conn.commit()
            batch = []

    if batch:
        insert_batch(cur, batch)
        conn.commit()

    cur.close()
    conn.close()

    print(f"[OK] {SYMBOL} imported.")

if __name__ == "__main__":
    main()
