"""Binance-Futures-compatible client for pbFinance, the simulator. SIMULATOR ONLY.

There is no live mode in this module and none should be added. A client whose
sim and live modes differ by base URL alone is one environment variable away
from real money; a validator that places orders must not be.
So the base URL has to pass BOTH:
  1. its host is in BTVAL_SIM_HOSTS (explicit allowlist, default
     'binance-simulator,pbfinance'), and
  2. the host is internal: a bare container name, *.local/*.internal, or a
     private/loopback IP. Any binance.com host is refused outright.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import math
import os
import time
import urllib.parse
from dataclasses import dataclass

import httpx
import pandas as pd

DEFAULT_SIM_HOSTS = "binance-simulator,pbfinance"


class NotASimulator(RuntimeError):
    pass


def _internal(host: str) -> bool:
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return ip.is_private or ip.is_loopback


def assert_sim_url(url: str, allow: str | None = None) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    allowed = {h.strip().lower() for h in (allow or os.environ.get("BTVAL_SIM_HOSTS", DEFAULT_SIM_HOSTS)).split(",") if h.strip()}
    if not host:
        raise NotASimulator(f"unparseable venue url {url!r}")
    if "binance" in host and "." in host:
        raise NotASimulator(f"{host} is a Binance host. btval only trades the simulator.")
    if host not in allowed:
        raise NotASimulator(f"{host} not in BTVAL_SIM_HOSTS {sorted(allowed)}")
    if not _internal(host):
        raise NotASimulator(f"{host} is not an internal address")
    return url.rstrip("/")


@dataclass
class SymbolFilters:
    step: float
    min_qty: float
    tick: float
    min_notional: float

    def round_qty(self, qty: float) -> float:
        n = math.floor(abs(qty) / self.step + 1e-9) * self.step
        dec = max(0, -int(math.floor(math.log10(self.step)))) if self.step < 1 else 0
        return round(math.copysign(n, qty), dec)


class SimVenue:
    def __init__(self, base_url: str, api_key: str, api_secret: str,
                 client: httpx.Client | None = None, allow_hosts: str | None = None, clock=time.time):
        self.base = assert_sim_url(base_url, allow_hosts)
        self.key, self.secret = api_key, api_secret.encode()
        self.http = client or httpx.Client(base_url=self.base, timeout=15.0)
        self._filters: dict[str, SymbolFilters] = {}
        self.clock = clock

    def _signed(self, method: str, path: str, params: dict) -> dict:
        p = {**params, "timestamp": int(time.time() * 1000), "recvWindow": 30000}
        qs = urllib.parse.urlencode(p)
        sig = hmac.new(self.secret, qs.encode(), hashlib.sha256).hexdigest()
        headers = {"X-MBX-APIKEY": self.key}
        if method == "POST":
            # Binance accepts signed params in the query or the body; pbFinance
            # reads POST params from the body only.
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            r = self.http.request(method, path, content=f"{qs}&signature={sig}", headers=headers)
        else:
            r = self.http.request(method, f"{path}?{qs}&signature={sig}", headers=headers)
        body = r.json()
        if r.status_code >= 400 or (isinstance(body, dict) and body.get("code", 0) < 0):
            raise RuntimeError(f"venue error {r.status_code}: {body}")
        return body

    def klines(self, symbol: str, interval: str, limit: int = 500) -> pd.Series:
        """CLOSED bars only, stamped at close time. The forming bar is dropped:
        acting on it is look-ahead with extra steps."""
        r = self.http.get("/fapi/v1/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
        r.raise_for_status()
        rows = r.json()
        now_ms = int(self.clock() * 1000)
        closed = [k for k in rows if int(k[6]) < now_ms]
        idx = pd.to_datetime([int(k[6]) + 1 for k in closed], unit="ms", utc=True).floor("s")
        return pd.Series([float(k[4]) for k in closed], index=idx, name="close")

    def filters(self, symbol: str) -> SymbolFilters:
        if symbol not in self._filters:
            r = self.http.get("/fapi/v1/exchangeInfo")
            r.raise_for_status()
            for s in r.json().get("symbols", []):
                f = {x["filterType"]: x for x in s.get("filters", [])}
                lot, pf, mn = f.get("LOT_SIZE", {}), f.get("PRICE_FILTER", {}), f.get("MIN_NOTIONAL", {})
                self._filters[s["symbol"]] = SymbolFilters(
                    step=float(lot.get("stepSize", 0.001)), min_qty=float(lot.get("minQty", 0.0)),
                    tick=float(pf.get("tickSize", 0.01)), min_notional=float(mn.get("notional", 5.0)))
        return self._filters[symbol]

    def market_order(self, symbol: str, qty: float, client_order_id: str, reduce_only: bool = False) -> dict:
        side = "BUY" if qty > 0 else "SELL"
        params = {"symbol": symbol, "side": side, "type": "MARKET", "quantity": abs(qty),
                  "newClientOrderId": client_order_id, "newOrderRespType": "RESULT"}
        if reduce_only:
            params["reduceOnly"] = "true"
        body = self._signed("POST", "/fapi/v1/order", params)
        # pbFinance answers HTTP 200 with status REJECTED (e.g. insufficient
        # margin). A 200 is not a fill.
        if str(body.get("status", "")).upper() != "FILLED" or float(body.get("executedQty") or 0) <= 0:
            raise RuntimeError(f"order not filled: status={body.get('status')} executedQty={body.get('executedQty')}")
        return body

    def position_amt(self, symbol: str) -> float:
        body = self._signed("GET", "/fapi/v2/positionRisk", {"symbol": symbol})
        return sum(float(p.get("positionAmt", 0)) for p in body if p.get("symbol") == symbol)
