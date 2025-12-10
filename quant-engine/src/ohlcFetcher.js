import fetch from "node-fetch";
import { pool } from "./db.js";

const BINANCE_API_URL = process.env.BINANCE_API_URL || "https://api.binance.com";
const LOOKBACK_DAYS = Number(process.env.QUANT_LOOKBACK_DAYS || 90);
const TIMEFRAME = "1d";
const SOURCE = "binance";

export async function fetchAndStoreDailyOhlc(symbol) {
  // Get approx LOOKBACK_DAYS candles from Binance
  const limit = Math.max(LOOKBACK_DAYS + 5, 30);
  const url = `${BINANCE_API_URL}/api/v3/klines?symbol=${symbol}&interval=1d&limit=${limit}`;

  let data;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.warn("[OHLC] Binance error for", symbol, res.status);
      return null;
    }
    data = await res.json();
  } catch (err) {
    console.warn("[OHLC] Fetch failed for", symbol, err.message);
    return null;
  }

  if (!Array.isArray(data) || data.length === 0) return null;

  const client = await pool.connect();
  try{
    await client.query("BEGIN");

    // optional: wipe recent OHLC for this symbol/timeframe/source
    await client.query(
      `
      DELETE FROM asset_ohlcv
      WHERE symbol = $1
        AND source = $2
        AND timeframe = $3;
      `,
      [symbol, SOURCE, TIMEFRAME]
    );

    // get asset_id if exists
    const assetRes = await client.query(
      "SELECT id FROM assets WHERE symbol = $1 LIMIT 1;",
      [symbol]
    );
    const assetId = assetRes.rows.length ? assetRes.rows[0].id : null;

    const insertText = `
      INSERT INTO asset_ohlcv (
        asset_id, symbol, source, timeframe,
        ts, open, high, low, close, volume
      )
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10);
    `;

    for (const k of data) {
      const openTimeMs = k[0];   // open time in ms
      const open = Number(k[1]);
      const high = Number(k[2]);
      const low = Number(k[3]);
      const close = Number(k[4]);
      const volume = Number(k[5]);
      // convert ms → timestamptz with timezone assumption
      const ts = new Date(openTimeMs).toISOString();

      await client.query(insertText, [
        assetId,
        symbol,
        SOURCE,
        TIMEFRAME,
        ts,
        open,
        high,
        low,
        close,
        volume
      ]);
    }

    await client.query("COMMIT");

    console.log(`[OHLC] Stored ${data.length} candles for ${symbol}`);
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("[OHLC] DB error for", symbol, err.message);
    return null;
  } finally {
    client.release();
  }

  return true;
}

export async function loadDailyOhlcFromDb(symbol) {
  const res = await pool.query(
    `
    SELECT ts, close
    FROM asset_ohlcv
    WHERE symbol = $1
      AND source = $2
      AND timeframe = $3
    ORDER BY ts ASC;
    `,
    [symbol, SOURCE, TIMEFRAME]
  );
  return res.rows.map((r) => ({
    ts: new Date(r.ts),
    close: Number(r.close)
  }));
}
