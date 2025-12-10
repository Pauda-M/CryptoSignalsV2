#!/usr/bin/env python3
import sys
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="summary")

# CORS FIX
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # allow frontend (localhost:8080)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "summary"}


import os
from typing import List
from pydantic import BaseModel
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class SummaryCard(BaseModel):
    title: str
    value: str
    color: str | None = None

class SummaryResponse(BaseModel):
    cards: List[SummaryCard]

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.get("/summary", response_model=SummaryResponse)
def summary():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM futures_transactions WHERE notional_usd > 10000;")
    big_trades = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM followed_wallets WHERE is_active = TRUE;")
    active_wallets = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COALESCE(SUM(xrp_volume),0), COALESCE(SUM(btc_volume),0)
        FROM xrp_btc_hourly_spread
        WHERE ts > NOW() - INTERVAL '24 hours';
        """
    )
    xrp_vol_24h, btc_vol_24h = cur.fetchone()

    cur.close()
    conn.close()

    cards = [
        SummaryCard(title="Big Futures Trades", value=str(big_trades), color="orange"),
        SummaryCard(title="Active Wallets", value=str(active_wallets), color="blue"),
        SummaryCard(title="XRP Volume 24h", value=f"{xrp_vol_24h:.0f}", color="green"),
        SummaryCard(title="BTC Volume 24h", value=f"{btc_vol_24h:.0f}", color="purple"),
    ]
    return SummaryResponse(cards=cards)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="0.0.0.0", port=9003)
