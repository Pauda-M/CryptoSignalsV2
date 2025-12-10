import express from "express";
import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

const router = express.Router();

const BINANCE = process.env.BINANCE_API_BASE || "https://api.binance.com";
const COINBASE = "https://api.exchange.coinbase.com";

function toCoinbaseProduct(symbol) {
  if (symbol.endsWith("USDT")) {
    const base = symbol.slice(0, -4);
    return `${base}-USDT`;
  }
  if (symbol.endsWith("USD")) {
    const base = symbol.slice(0, -3);
    return `${base}-USD`;
  }
  return symbol;
}

async function fetchBinanceKlines(symbol, interval, limit) {
  const url = `${BINANCE}/api/v3/klines?symbol=${encodeURIComponent(
    symbol
  )}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`BINANCE_${res.status}`);
  const data = await res.json();
  return data.map((k) => ({
    time: k[0],
    open: parseFloat(k[1]),
    high: parseFloat(k[2]),
    low: parseFloat(k[3]),
    close: parseFloat(k[4]),
    volume: parseFloat(k[5])
  }));
}

async function fetchCoinbaseCandles(symbol, granularitySeconds, limit) {
  const product = toCoinbaseProduct(symbol);
  const url = `${COINBASE}/products/${product}/candles?granularity=${granularitySeconds}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`COINBASE_${res.status}`);
  const data = await res.json();
  const sorted = data.sort((a, b) => a[0] - b[0]).slice(-limit);
  return sorted.map((c) => ({
    time: c[0] * 1000,
    open: c[3],
    high: c[2],
    low: c[1],
    close: c[4],
    volume: c[5]
  }));
}

function intervalToSeconds(interval) {
  if (interval.endsWith("m")) return parseInt(interval) * 60;
  if (interval.endsWith("h")) return parseInt(interval) * 3600;
  if (interval.endsWith("d")) return parseInt(interval) * 86400;
  return 900;
}

router.get("/klines", async (req, res) => {
  const symbol = (req.query.symbol || "BTCUSDT").toUpperCase();
  const interval = req.query.interval || "15m";
  const limit = parseInt(req.query.limit || "200", 10);

  try {
    try {
      const candles = await fetchBinanceKlines(symbol, interval, limit);
      return res.json({ source: "binance", candles });
    } catch (e) {
      console.warn("[MARKET] Binance failed, trying Coinbase:", e.message);
      const gran = intervalToSeconds(interval);
      const candles = await fetchCoinbaseCandles(symbol, gran, limit);
      return res.json({ source: "coinbase", candles });
    }
  } catch (err) {
    console.error("[MARKET] Failed to fetch candles", err);
    res.status(500).json({ error: "Market data error" });
  }
});

export default router;
