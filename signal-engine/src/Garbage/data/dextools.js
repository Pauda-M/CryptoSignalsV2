// src/data/dextools.js
import fetch from "node-fetch";

export async function fetchDexToolsPool(chain, poolAddress) {
  try {
    const url = `https://www.dextools.io/shared/data/pool/${chain}/${poolAddress}`;
    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0"
      }
    });

    const data = await res.json();

    return {
      priceUsd: data?.price || 0,
      volume24hUsd: data?.volume24h || 0,
      liquidityUsd: data?.liquidity || 0,
    };
  } catch (err) {
    return null;
  }
}
