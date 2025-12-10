
import os
import time
import requests
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# psycopg2 requires "postgres://" not "postgresql://"
if DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgres://")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()


DATABASE_URL = os.getenv("DATABASE_URL")

def ts(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS market_candles(
        exchange TEXT,
        symbol TEXT,
        interval TEXT,
        open_time TIMESTAMPTZ,
        close_time TIMESTAMPTZ,
        open NUMERIC,
        high NUMERIC,
        low NUMERIC,
        close NUMERIC,
        volume NUMERIC,
        quote_volume NUMERIC,
        trades_count INT,
        taker_buy_base_volume NUMERIC,
        taker_buy_quote_volume NUMERIC,
        is_closed BOOLEAN,
        PRIMARY KEY(exchange, symbol, interval, open_time)
    );""")
    cur.execute("DROP TABLE IF EXISTS xrp_btc_hourly_spread;")
    cur.execute("""CREATE TABLE IF NOT EXISTS xrp_btc_hourly_spread(
        ts TIMESTAMPTZ PRIMARY KEY,
        spread_log NUMERIC,
        xrp_volume NUMERIC,
        btc_volume NUMERIC
    );""")
    conn.commit()
    cur.close()
    print("[INFO] ensure_schema done")

BINANCE_URL = "https://api.binance.com/api/v3/klines"

def fetch_klines(symbol: str, interval="15min", start_ts=None, end_ts=None):
    out = []
    limit = 1000
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    t = start_ts
    print(f"[INFO] Fetching {symbol} ...")
    while True:
        params["startTime"] = int(t.timestamp() * 1000)
        r = requests.get(BINANCE_URL, params=params)
        if r.status_code != 200:
            print("Error:", r.text)
            break
        data = r.json()
        if not data:
            break
        for k in data:
            open_time = k[0]
            if end_ts and ts(open_time) > end_ts:
                return out
            out.append(k)
        if len(data) < limit:
            break
        last_open = data[-1][0]
        t = ts(last_open) + timedelta(minutes=15)
        time.sleep(0.3)
    return out

def upsert_market_candle(cur, exchange, symbol, interval, k):
    open_time = ts(k[0])
    close_time = ts(k[6])
    cur.execute(
        '''
        INSERT INTO market_candles(
          exchange, symbol, interval, open_time, close_time,
          open, high, low, close, volume, quote_volume,
          trades_count, taker_buy_base_volume, taker_buy_quote_volume, is_closed
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
        ON CONFLICT (exchange, symbol, interval, open_time)
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
        ''',
        (
            exchange, symbol, interval,
            open_time, close_time,
            k[1], k[2], k[3], k[4], k[5],
            k[7], k[8], k[9], k[10]
        ),
    )

def rebuild_spread_hourly(conn):
    cur = conn.cursor()
    print("[INFO] Rebuilding xrp_btc_hourly_spread ...")
    cur.execute("DELETE FROM xrp_btc_hourly_spread;")
    cur.execute(
        '''
        INSERT INTO xrp_btc_hourly_spread(ts, spread_log, xrp_volume, btc_volume)
        SELECT
            c1.open_time AS ts,
            LN(CAST(c1.close AS DOUBLE PRECISION) / CAST(c2.close AS DOUBLE PRECISION)) AS spread_log,
            CAST(c1.volume AS DOUBLE PRECISION),
            CAST(c2.volume AS DOUBLE PRECISION)
        FROM market_candles c1
        JOIN market_candles c2
            ON c1.open_time = c2.open_time
           AND c1.interval = c2.interval
        WHERE c1.symbol='XRPUSDT' AND c2.symbol='BTCUSDT' AND c1.interval='15m'
        ORDER BY ts ASC;
        '''
    )
    conn.commit()
    cur.close()
    print("[INFO] Spread table rebuilt.")

def seed_futures_transactions(conn):
    print("[INFO] futures_transactions left empty for realtime ingest.")

def seed_followed_wallets(conn):
    print("[INFO] followed_wallets left empty (user-managed).")

def main():
    conn = get_conn()
    ensure_schema(conn)
    cur = conn.cursor()
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=365*3)
    print("[INFO] Downloading BTCUSDT 15m history ...")
    btc = fetch_klines("BTCUSDT", "15m", start_date, end_date)
    print("[INFO] Downloading XRPUSDT 15m history ...")
    xrp = fetch_klines("XRPUSDT", "15m", start_date, end_date)
    print(f"[INFO] Inserting BTCUSDT ({len(btc)}) rows ...")
    for k in btc:
        upsert_market_candle(cur, "binance", "BTCUSDT", "15m", k)
    conn.commit()
    print(f"[INFO] Inserting XRPUSDT ({len(xrp)}) rows ...")
    for k in xrp:
        upsert_market_candle(cur, "binance", "XRPUSDT", "15m", k)
    conn.commit()
    rebuild_spread_hourly(conn)
    seed_futures_transactions(conn)
    seed_followed_wallets(conn)
    cur.close()
    conn.close()
    print("[DONE] 3-year history download complete.")

if __name__ == "__main__":
    main()
