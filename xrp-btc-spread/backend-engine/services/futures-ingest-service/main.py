#!/usr/bin/env python3
import sys
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Futures Ingest Service")
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/health")
def health():
    return {"status": "ok", "service": "Futures Ingest Service"}


import os
import asyncio
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
import psycopg2
import websockets

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BINANCE_FUTURES_WSS = "wss://fstream.binance.com/stream?streams=btcusdt@aggTrade/xrpusdt@aggTrade"

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def now_utc():
    return datetime.now(tz=timezone.utc)

def insert_futures_trade(conn, symbol, price, quantity, notional_usd, side, trade_time):
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO futures_transactions (symbol, tx_time, side, price, quantity, notional_usd, success_rate)
        VALUES (%s,%s,%s,%s,%s,%s,NULL);
        ''',
        (symbol, trade_time, side, price, quantity, notional_usd),
    )
    conn.commit()
    cur.close()

async def run_futures_stream():
    conn = get_conn()
    while True:
        try:
            async with websockets.connect(BINANCE_FUTURES_WSS, ping_interval=20, ping_timeout=20) as ws:
                print("[futures-ingest] connected to Binance Futures WSS")
                async for msg in ws:
                    data = json.loads(msg)
                    payload = data.get("data")
                    if not payload:
                        continue
                    s = payload.get("s")
                    p = float(payload.get("p", 0.0))
                    q = float(payload.get("q", 0.0))
                    m = payload.get("m")
                    notional = p * q
                    if notional < 10000:
                        continue
                    side = "SELL" if m else "BUY"
                    t = payload.get("T")
                    tx_time = datetime.fromtimestamp(t/1000.0, tz=timezone.utc) if t else now_utc()
                    try:
                        insert_futures_trade(conn, s, p, q, notional, side, tx_time)
                    except Exception as e:
                        print("[futures-ingest] insert error:", e)
        except Exception as e:
            print("[futures-ingest] stream error:", e)
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_futures_stream())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="0.0.0.0", port=9102)
