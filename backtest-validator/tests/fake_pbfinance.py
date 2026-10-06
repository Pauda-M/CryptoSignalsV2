"""In-process stand-in for pbFinance (Binance Futures API shape) via httpx.MockTransport."""
import json
import time
import urllib.parse

import httpx
import numpy as np


class FakePbFinance:
    def __init__(self, closes, interval_ms=86_400_000, fill_offset_bps=2.0, symbol="BTCUSDT"):
        self.closes = list(closes)
        self.interval_ms = interval_ms
        self.fill_offset_bps = fill_offset_bps
        self.symbol = symbol
        self.position = 0.0
        self.orders = []
        self.seen_client_ids = set()
        self.reject_next = False
        self.live_price = None
        real = int(time.time() * 1000)
        self.anchor = real - real % interval_ms - (len(self.closes) - 1) * interval_ms  # open of bar 0
        self.now_ms = real

    def clock(self):
        return self.now_ms / 1000

    def advance(self, close):
        """Close the forming bar and start a new one at `close`."""
        self.closes.append(close)
        self.now_ms += self.interval_ms

    def _klines(self, limit):
        out = []
        for i, c in enumerate(self.closes):  # last element is the FORMING bar
            o = self.anchor + i * self.interval_ms
            out.append([o, c, c, c, c, 1.0, o + self.interval_ms - 1, 0, 0, 0, 0, 0])
        return out[-limit:]

    def handler(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path
        q = dict(urllib.parse.parse_qsl(req.url.query.decode()))
        if req.method == "POST":  # like pbFinance: POST params come from the body ONLY
            q = dict(urllib.parse.parse_qsl(req.content.decode()))
        if path == "/fapi/v1/klines":
            return httpx.Response(200, json=self._klines(int(q.get("limit", 500))))
        if path == "/fapi/v1/ticker/price":
            return httpx.Response(200, json={"symbol": q.get("symbol"), "price": str(self.live_price or self.closes[-1])})
        if path == "/fapi/v1/exchangeInfo":
            return httpx.Response(200, json={"symbols": [{"symbol": self.symbol, "filters": [
                {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
                {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
                {"filterType": "MIN_NOTIONAL", "notional": "5"}]}]})
        if "signature" not in q or not req.headers.get("X-MBX-APIKEY"):
            return httpx.Response(401, json={"code": -2015, "msg": "unsigned"})
        if path == "/fapi/v1/order" and req.method == "POST":
            if q["newClientOrderId"] in self.seen_client_ids:
                return httpx.Response(400, json={"code": -4015, "msg": "duplicate clientOrderId"})
            self.seen_client_ids.add(q["newClientOrderId"])
            qty = float(q["quantity"]) * (1 if q["side"] == "BUY" else -1)
            if self.reject_next:  # pbFinance: insufficient margin -> 200 + REJECTED
                self.reject_next = False
                return httpx.Response(200, json={"orderId": 0, "status": "REJECTED", "avgPrice": "0",
                                                 "executedQty": "0.0"})
            # pbFinance nets an opposite-side order correctly only with reduceOnly
            if self.position and np.sign(qty) != np.sign(self.position) and q.get("reduceOnly") != "true":
                return httpx.Response(200, json={"orderId": 0, "status": "FILLED", "avgPrice": "1",
                                                 "executedQty": q["quantity"], "note": "would corrupt netting"})
            if q.get("reduceOnly") == "true" and abs(qty) > abs(self.position) + 1e-12:
                return httpx.Response(400, json={"code": -2022, "msg": "ReduceOnly Order is rejected."})
            ref = self.closes[-2]
            avg = ref * (1 + np.sign(qty) * self.fill_offset_bps / 1e4)
            self.position += qty
            self.orders.append(q)
            return httpx.Response(200, json={"orderId": len(self.orders), "status": "FILLED",
                                             "avgPrice": f"{avg:.4f}", "executedQty": q["quantity"],
                                             "clientOrderId": q["newClientOrderId"]})
        if path == "/fapi/v2/positionRisk":
            return httpx.Response(200, json=[{"symbol": self.symbol, "positionAmt": str(self.position)}])
        return httpx.Response(404, json={"code": -1, "msg": path})

    def client(self, base="http://binance-simulator:8976"):
        return httpx.Client(base_url=base, transport=httpx.MockTransport(self.handler))
