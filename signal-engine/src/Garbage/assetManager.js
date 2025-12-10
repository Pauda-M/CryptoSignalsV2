import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

const BACKEND = process.env.BACKEND_URL || "http://localhost:4000";

export async function assetExists(symbol) {
  const res = await fetch(`${BACKEND}/api/assets`);
  if (!res.ok) {
    console.error("[ASSETS] Failed to fetch assets:", res.status);
    return false;
  }
  const assets = await res.json();
  return assets.some((a) => a.symbol.toUpperCase() === symbol.toUpperCase());
}

export async function createAsset(symbol) {
  const base = symbol.slice(0, -4);
  const quote = symbol.slice(-4);

  const payload = {
    symbol: symbol.toUpperCase(),
    name: `${base}/${quote}`,
    base_asset: base,
    quote_asset: quote
  };

  console.log("[ASSETS] Creating asset", payload.symbol);

  const res = await fetch(`${BACKEND}/api/assets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const text = await res.text();
    console.error("[ASSETS] Create failed:", text);
    throw new Error("Asset creation failed");
  }

  return await res.json();
}
