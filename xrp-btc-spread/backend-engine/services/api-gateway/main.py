import sys
import httpx
from fastapi import FastAPI, HTTPException
import asyncio

import uvicorn
app = FastAPI(title="API-Gateway v2")



# ----------------------------------------------------------
# CORS (GLOBAL)
# ----------------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # allow dashboard at :8080
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------
# BACKEND SERVICE PORTS
# ----------------------------------------------------------
BACKEND = {
    "predictions": "http://localhost:9101",
    "futures":  "http://localhost:9001",
    "wallets":  "http://localhost:9002",
    "summary":  "http://localhost:9003",
}

# ----------------------------------------------------------
# Simple logger
# ----------------------------------------------------------
def log(msg: str):
    print(f"[GATEWAY] {msg}")

# ----------------------------------------------------------
# Retry wrapper for backend service calls
# ----------------------------------------------------------
async def fetch_with_retry(url, retries=3, timeout=6.0):
    async with httpx.AsyncClient(timeout=timeout) as client:
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                log(f"Request → {url} (attempt {attempt})")
                r = await client.get(url)

                # Accept only valid JSON
                if r.status_code == 200:
                    log(f"Response OK ← {url}")
                    return r.json()

                log(f"Bad response {r.status_code} from {url}")
                last_exc = HTTPException(r.status_code, r.text)

            except Exception as e:
                log(f"Request failed: {e}")
                last_exc = e

            await asyncio.sleep(0.3)  # small retry delay

        raise HTTPException(status_code=500, detail=f"Backend unreachable: {url}, Last error: {last_exc}")

# ----------------------------------------------------------
# HEALTHCHECK
# ----------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# ----------------------------------------------------------
# PREDICTIONS ROUTE
# ----------------------------------------------------------

@app.get("/api/predictions")
async def proxy_predictions():
    url = BACKEND["predictions"] + "/api/predictions"
    return await fetch_with_retry(url)

# ----------------------------------------------------------
# FUTURES ROUTE
# ----------------------------------------------------------
@app.get("/api/futures")
async def proxy_futures():
    url = BACKEND["futures"] + "/futures"
    return await fetch_with_retry(url)

# ----------------------------------------------------------
# WALLETS ROUTE
# ----------------------------------------------------------
@app.get("/api/wallets")
async def proxy_wallets():
    url = BACKEND["wallets"] + "/wallets"
    return await fetch_with_retry(url)

# ----------------------------------------------------------
# EXEC SUMMARY ROUTE
# ----------------------------------------------------------
@app.get("/api/summary")
async def proxy_summary():
    url = BACKEND["summary"] + "/summary"
    return await fetch_with_retry(url)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    uvicorn.run(app, host="0.0.0.0", port=9000)
