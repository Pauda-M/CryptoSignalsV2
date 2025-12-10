import fetch from "node-fetch";
import dotenv from "dotenv";
import { postCoreSignalToBackend } from "./backendClient.js";

dotenv.config();

const BINANCE_API_URL = process.env.BINANCE_API_URL || "https://api.binance.com";
const CORE_SYMBOLS = (process.env.CORE_SYMBOLS || "BTCUSDT,ETHUSDT")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const CORE_TIMEFRAME = process.env.CORE_TIMEFRAME || "15m";
const CORE_LOOP_INTERVAL_MS = Number(
  process.env.CORE_LOOP_INTERVAL_MS || 60_000
);

async function fetchLastCandle(symbol, interval) {
  const url = `${BINANCE_API_URL}/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=50`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Binance klines ${res.status}`);
  }
  const data = await res.json();
  const close = Number(data[data.length - 1][4]);
  const prevClose = Number(data[data.length - 2][4]);
  const change = (close - prevClose) / prevClose;
  return { close, change };
}

function directionFromChange(change) {
  if (change > 0.002) return "BUY";
  if (change < -0.002) return "SELL";
  return "HOLD";
}

export async function generateCoreSignal(symbol, timeframe) {
  try {
    const { close, change } = await fetchLastCandle(symbol, timeframe);
    const direction = directionFromChange(change);
    const confidence = Math.min(1, Math.abs(change) * 200); // simple scaling

    const payload = {
      symbol,
      timeframe,
      model_name: "core_binance_v1",
      direction,
      confidence,
      entry_price: close,
      stop_loss: direction === "BUY" ? close * 0.98 : close * 1.02,
      take_profit: direction === "BUY" ? close * 1.02 : close * 0.98
    };

    await postCoreSignalToBackend(payload);
    console.log(
      `[CORE] ${symbol} ${direction} conf=${(confidence * 100).toFixed(1)}%`
    );
  } catch (err) {
    console.error("[CORE] Error for", symbol, err.message);
  }
}

export function startCoreEngineLoop() {
  console.log(
    `[CORE] Starting core engine loop every ${
      CORE_LOOP_INTERVAL_MS / 1000
    }s for ${CORE_SYMBOLS.join(", ")}`
  );

  const loop = async () => {
    for (const sym of CORE_SYMBOLS) {
      await generateCoreSignal(sym, CORE_TIMEFRAME);
      await new Promise((r) => setTimeout(r, 300));
    }
    setTimeout(loop, CORE_LOOP_INTERVAL_MS);
  };

  loop();
}
