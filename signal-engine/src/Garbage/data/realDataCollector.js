// src/data/realDataCollector.js
import { fetchDexScreener } from "./dexScreener.js";
import { fetchPumpfunTrending } from "./pumpfun.js";

export async function collectRealMemeData(symbolList) {
  const result = [];

  for (const symbol of symbolList) {
    const dex = await fetchDexScreener(symbol);
    const pump = await fetchPumpfunTrending();

    const pf = pump.find(x => x.symbol === symbol);

    result.push({
      symbol,
      price: dex?.priceUsd ?? 0,
      liquidityUsd: dex?.liquidityUsd ?? 0,
      volumeUsd: dex?.volume24hUsd ?? 0,
      buys5m: dex?.buys5m ?? 0,
      sells5m: dex?.sells5m ?? 0,
      marketcap: pf?.marketcap ?? 0,
      holders: pf?.holders ?? 0,
      ageSeconds: pf?.ageSeconds ?? 0,
      dex: dex?.dex ?? null
    });
  }

  return result;
}
