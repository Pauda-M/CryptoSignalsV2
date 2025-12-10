import fetch from "node-fetch";

/* --------------------------- PUMPFUN TOP MEMES --------------------------- */
async function fetchPumpFun() {
  try {
    const r = await fetch("https://pump.fun/api/trending");
    const js = await r.json();

    return js.tokens.map(t => ({
      symbol: t.symbol,
      marketcap: t.market_cap ?? 0,
      liquidityusd: t.liquidity_usd ?? 0,
      volumeusd: t.volume_usd_24h ?? 0,
      holders: t.holder_count ?? 0,
      pumpfun_score: t.score ?? 0
    }));
  } catch (err) {
    console.error("[PUMPFUN] error", err);
    return [];
  }
}

/* ----------------------------- DEXTOOLS HOT PAIRS ----------------------------- */
async function fetchDexTools() {
  try {
    const r = await fetch("https://www.dextools.io/shared/analytics/hotpairs");
    const js = await r.json();

    return js.data.map(t => ({
      symbol: t.symbol,
      marketcap: t.marketCap ?? 0,
      liquidityusd: t.liquidity ?? 0,
      volumeusd: t.volume24h ?? 0,
      dex_score: t.score ?? 0
    }));
  } catch (err) {
    console.error("[DEXTOOLS] error", err);
    return [];
  }
}

/* ---------------------------- DEXSCREENER TRENDING ---------------------------- */
async function fetchDexScreener() {
  try {
    const r = await fetch("https://api.dexscreener.com/latest/dex/tokens/trending");
    const js = await r.json();

    return js.pairs.map(p => ({
      symbol: p.baseToken.symbol,
      marketcap: p.fdv ?? 0,
      liquidityusd: p.liquidity?.usd ?? 0,
      volumeusd: p.volume?.h24 ?? 0,
      bitquery_score: p.txns?.h1?.buys ?? 0
    }));
  } catch (err) {
    console.error("[DEXSCREENER] error", err);
    return [];
  }
}

/* ----------------------------- MERGE + CLEAN OUTPUT ---------------------------- */
export async function fetchTrendingTokens() {
  const data = [
    ...(await fetchPumpFun()),
    ...(await fetchDexTools()),
    ...(await fetchDexScreener())
  ];

  // merge by symbol
  const map = new Map();
  for (const t of data) {
    const prev = map.get(t.symbol) || {};
    map.set(t.symbol, { ...prev, ...t });
  }

  return [...map.values()].filter(t => t.symbol);
}
