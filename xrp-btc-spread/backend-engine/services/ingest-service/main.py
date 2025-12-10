#!/usr/bin/env python3
import sys
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Ingest Service")
# CORS
from fastapi.middleware.cors import CORSMiddleware  
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/health")
def health():
    return {"status": "ok", "service": "Ingest Service"}


import os
import asyncio
import json
from datetime import datetime, timezone

import psycopg2
import websockets
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BINANCE_WSS_URL = "wss://stream.binance.com:9443/stream?streams=btcusdt@kline_1h/xrpusdt@kline_1h"

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def ms_to_ts(ms):
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)

def upsert_candle(conn, payload):
    cur = conn.cursor()
    k = payload["k"]
    symbol = k["s"].upper()
    interval = k["i"]
    open_time = ms_to_ts(k["t"])
    close_time = ms_to_ts(k["T"])
    o = k["o"]; h = k["h"]; l = k["l"]; c = k["c"]; v = k["v"]
    q = k.get("q"); n = k.get("n"); V = k.get("V"); Q = k.get("Q")
    is_closed = k["x"]
    sql = '''
    INSERT INTO market_candles
      (exchange, symbol, interval, open_time, close_time,
       open, high, low, close, volume, quote_volume,
       trades_count, taker_buy_base_volume, taker_buy_quote_volume, is_closed)
    VALUES
      (%(exchange)s, %(symbol)s, %(interval)s, %(open_time)s, %(close_time)s,
       %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(quote_volume)s,
       %(trades_count)s, %(taker_buy_base_volume)s, %(taker_buy_quote_volume)s, %(is_closed)s)
    ON CONFLICT (exchange, symbol, interval, open_time)
    DO UPDATE SET
       close_time = EXCLUDED.close_time,
       open       = EXCLUDED.open,
       high       = EXCLUDED.high,
       low        = EXCLUDED.low,
       close      = EXCLUDED.close,
       volume     = EXCLUDED.volume,
       quote_volume = EXCLUDED.quote_volume,
       trades_count = EXCLUDED.trades_count,
       taker_buy_base_volume  = EXCLUDED.taker_buy_base_volume,
       taker_buy_quote_volume = EXCLUDED.taker_buy_quote_volume,
       is_closed  = EXCLUDED.is_closed;
    '''
    params = {
        "exchange": "binance",
        "symbol": symbol,
        "interval": interval,
        "open_time": open_time,
        "close_time": close_time,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "quote_volume": q,
        "trades_count": n,
        "taker_buy_base_volume": V,
        "taker_buy_quote_volume": Q,
        "is_closed": is_closed,
    }
    cur.execute(sql, params)
    conn.commit()
    cur.close()

async def run_ingestion():
    conn = get_conn()
    while True:
        try:
            async with websockets.connect(BINANCE_WSS_URL, ping_interval=20, ping_timeout=20) as ws:
                print("Ingest-service connected to Binance WSS")
                async for msg in ws:
                    data = json.loads(msg)
                    payload = data.get("data")
                    if not payload or payload.get("e") != "kline":
                        continue
                    upsert_candle(conn, payload)
        except Exception as e:
            print("Ingest error:", e)
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_ingestion())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="0.0.0.0", port=9004)
