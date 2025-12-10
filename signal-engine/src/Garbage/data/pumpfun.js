// src/data/pumpfun.js
import fetch from "node-fetch";

export async function fetchPumpfunTrending() {
  try {
    const url = "https://frontend-api.pump.fun/trpc/trending.all";
    const res = await fetch(url);
    const json = await res.json();

    const list = json?.result?.data?.json || [];

    return list.map(t => ({
      symbol: t.symbol,
      name: t.name,
      holders: t.holders,
      ageSeconds: t.age,
      marketcap: Number(t.marketCapUsd || 0),
      volumeUsd: Number(t.volumeUsd || 0)
    }));
  } catch (err) {
    return [];
  }
}
