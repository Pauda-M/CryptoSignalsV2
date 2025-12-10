#!/usr/bin/env python3
import sys
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Wallets Service")
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
    return {"status": "ok", "service": "Wallets Service"}


import os
from typing import List
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class Wallet(BaseModel):
    id: int
    chain: str
    address: str
    label: str | None
    is_active: bool

class WalletCreate(BaseModel):
    chain: str
    address: str
    label: str | None = None

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.get("/wallets", response_model=List[Wallet])
def list_wallets():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, chain, address, label, is_active FROM followed_wallets ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [Wallet(**dict(r)) for r in rows]

@app.post("/wallets", response_model=Wallet)
def add_wallet(w: WalletCreate):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        INSERT INTO followed_wallets (chain, address, label, is_active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (chain, address)
        DO UPDATE SET label = EXCLUDED.label, is_active = TRUE
        RETURNING id, chain, address, label, is_active;
        """
        ,
        (w.chain, w.address, w.label),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return Wallet(**dict(row))

@app.post("/wallets/{wallet_id}/toggle", response_model=Wallet)
def toggle_wallet(wallet_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        UPDATE followed_wallets
        SET is_active = NOT is_active
        WHERE id = %s
        RETURNING id, chain, address, label, is_active;
        """
        ,
        (wallet_id,),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return Wallet(**dict(row))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("main:app", host="0.0.0.0", port=9002)
