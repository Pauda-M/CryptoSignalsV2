// src/data/dexScreener.js
import fetch from "node-fetch";

export async function fetchDexScreener(symbol) {
  try {
    const url = `https://api.dexscreener.io/latest/dex/search?q=${symbol}`;
    const res = await fetch(url);
    const data = await res.json();

    if (!data.pairs || data.pairs.length === 0) return null;

    // pick best pair
    const p = data.pairs[0];

    return {
      symbol,
      priceUsd: Number(p.priceUsd || 0),
      liquidityUsd: Number(p.liquidity?.usd || 0),
      volume24hUsd: Number(p.volume?.h24 || 0),
      buys5m: Number(p.txns?.m5?.buys || 0),
      sells5m: Number(p.txns?.m5?.sells || 0),
      fdv: Number(p.fdv || 0),
      baseToken: p.baseToken?.symbol || symbol,
      dex: p.dexId,
    };
  } catch (err) {
    return null;
  }
}
