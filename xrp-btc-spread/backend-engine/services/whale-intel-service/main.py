import asyncio
import json
from datetime import datetime, timezone
import aiohttp
import psycopg2
from fastapi import FastAPI

app = FastAPI()

PG = {
    "host": "pbcryptodb01",
    "port": 5432,
    "user": "postgres",
    "password": "KarmaKoma2024",
    "dbname": "crypto_signals"
}

WH_THRESHOLD_USD = 250000  # configurable


def db():
    return psycopg2.connect(**PG)


def save_whale(chain, wallet_from, wallet_to, asset, amount_usd, tx_hash, raw):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO whale_transfers (
            chain, wallet_from, wallet_to, asset, amount_usd,
            direction, exchange_target, tx_hash, ts, raw
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        chain,
        wallet_from,
        wallet_to,
        asset,
        amount_usd,
        "unknown",       # Direction evaluated later
        None,            # Exchange evaluated later
        tx_hash,
        datetime.now(tz=timezone.utc),
        json.dumps(raw)
    ))

    conn.commit()
    cur.close()
    conn.close()


# ------------------------------------------------------
# BTC mempool
# ------------------------------------------------------
async def watch_btc():
    url = "https://mempool.space/api/mempool/recent"

    while True:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url) as r:
                    data = await r.json()

                for tx in data:
                    value = tx.get("value", 0) / 1e8
                    # Price is unknown now → skip USD calc
                    # Will score later in intel-service
                    usd = value * 40000  # TEMP until price service exists

                    if usd >= WH_THRESHOLD_USD:
                        save_whale(
                            "btc",
                            tx.get("vin", [{}])[0].get("prevout", {}).get("scriptpubkey_address", ""),
                            tx.get("vout", [{}])[0].get("scriptpubkey_address", ""),
                            "BTC",
                            usd,
                            tx.get("txid"),
                            tx
                        )
        except Exception:
            pass

        await asyncio.sleep(5)


# ------------------------------------------------------
# ETH ERC20 transfers (RWA tokens)
# ------------------------------------------------------
ETH_TOKENS = {
    # CONTRACT                                 # NAME
    "0x3449fc1cd036255ba1eb19d65ff4baa2a6ea0c54": "ONDO",
    "0xefd6c9fb2108c48c59a386680f3c75e0b43b37f0": "PYUSD",
    "0xaeaee2e6eb474d4bf4a6a2f8e8ad3a4d8f23d5a9": "POLYX",
    "0x4d5c9048ba2f2eea5fb8c0d24dd47cebbf2b5e83": "USDM",
    "0x8dd8b094a548df29359f6f8f6f792c42f04238b4": "EURC",
}

ETHERSCAN = "https://api.etherscan.io/api"
APIKEY = "YourEtherscanKey"


async def watch_eth():
    while True:
        try:
            for contract, symbol in ETH_TOKENS.items():
                params = {
                    "module": "account",
                    "action": "tokentx",
                    "contractaddress": contract,
                    "sort": "desc",
                    "apikey": APIKEY
                }

                async with aiohttp.ClientSession() as sess:
                    async with sess.get(ETHERSCAN, params=params) as r:
                        raw = await r.json()

                txs = raw.get("result", [])
                for tx in txs[:5]:
                    amount = float(tx["value"]) / 10**int(tx["tokenDecimal"])
                    usd = amount * 1.0  # price proxy until price service

                    if usd >= WH_THRESHOLD_USD:
                        save_whale(
                            "eth",
                            tx["from"],
                            tx["to"],
                            symbol,
                            usd,
                            tx["hash"],
                            tx
                        )
        except Exception:
            pass

        await asyncio.sleep(4)


# ------------------------------------------------------
# SOL (simplified demo version)
# ------------------------------------------------------
async def watch_sol():
    await asyncio.sleep(10)   # disabled until Solana endpoint added


# ------------------------------------------------------
# Startup
# ------------------------------------------------------
@app.on_event("startup")
async def startup():
    asyncio.create_task(watch_btc())
    asyncio.create_task(watch_eth())
    asyncio.create_task(watch_sol())
    print("Whale ingest running.")


@app.get("/")
def root():
    return {"status": "whale-ingest running"}
