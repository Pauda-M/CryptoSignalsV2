#!/usr/bin/env python3
import sys
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Futures Service")
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
    return {"status": "ok", "service": "Futures Service"}


import os
from typing import List
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class FuturesRow(BaseModel):
    symbol: str
    tx_time: str
    side: str
    price: float
    quantity: float
    notional_usd: float
    success_rate: float | None

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.get("/futures", response_model=List[FuturesRow])
def get_futures():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        SELECT symbol, tx_time, side, price, quantity, notional_usd, success_rate
        FROM futures_transactions
        WHERE notional_usd > 10000
        ORDER BY tx_time DESC
        LIMIT 200;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    out = []
    for r in rows:
        out.append(
            FuturesRow(
                symbol=r["symbol"],
                tx_time=r["tx_time"].isoformat(),
                side=r["side"],
                price=float(r["price"]),
                quantity=float(r["quantity"]),
                notional_usd=float(r["notional_usd"]),
                success_rate=float(r["success_rate"]) if r["success_rate"] is not None else None,
            )
        )
    return out


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="0.0.0.0", port=9001)
