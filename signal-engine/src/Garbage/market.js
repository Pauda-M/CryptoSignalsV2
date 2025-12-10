import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

const BINANCE_API_BASE = process.env.BINANCE_API_BASE || "https://api.binance.com";
const COINBASE_API_BASE = "https://api.exchange.coinbase.com";

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

export async function fetchBinanceKlines(symbol, interval, limit = 200) {
  const url = `${BINANCE_API_BASE}/api/v3/klines?symbol=${encodeURIComponent(
    symbol
  )}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`BINANCE_${res.status}`);
  const data = await res.json();
  return data.map((k) => ({
    openTime: k[0],
    open: parseFloat(k[1]),
    high: parseFloat(k[2]),
    low: parseFloat(k[3]),
    close: parseFloat(k[4]),
    volume: parseFloat(k[5]),
    closeTime: k[6]
  }));
}

export async function fetchCoinbaseCandles(symbol, granularitySeconds, limit = 200) {
  const product = toCoinbaseProduct(symbol);
  const url = `${COINBASE_API_BASE}/products/${product}/candles?granularity=${granularitySeconds}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`COINBASE_${res.status}`);
  const data = await res.json();
  const sorted = data.sort((a, b) => a[0] - b[0]).slice(-limit);
  return sorted.map((c) => ({
    openTime: c[0] * 1000,
    open: c[3],
    high: c[2],
    low: c[1],
    close: c[4],
    volume: c[5],
    closeTime: c[0] * 1000
  }));
}

function intervalToSeconds(interval) {
  if (interval.endsWith("m")) return parseInt(interval) * 60;
  if (interval.endsWith("h")) return parseInt(interval) * 3600;
  if (interval.endsWith("d")) return parseInt(interval) * 86400;
  return 900;
}

export async function fetchKlines(symbol, interval, limit = 200) {
  try {
    return await fetchBinanceKlines(symbol, interval, limit);
  } catch (err) {
    console.warn("[MARKET] Binance failed, trying Coinbase:", err.message);
    const gran = intervalToSeconds(interval);
    return await fetchCoinbaseCandles(symbol, gran, limit);
  }
}

export function computePriceMomentum(candles, lookback = 50) {
  if (!candles || candles.length < lookback + 1) return 0;
  const last = candles[candles.length - 1];
  const slice = candles.slice(-lookback);
  const sma = slice.reduce((sum, c) => sum + c.close, 0) / slice.length;
  const ratio = (last.close - sma) / sma;
  const capped = Math.max(-0.1, Math.min(0.1, ratio));
  return capped / 0.1;
}
