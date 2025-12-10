// ===========================================================
//  memeEngine.js — Meme Alpha Engine v5
//  Clean, DB-free engine that fetches data, computes features,
//  evaluates ML alpha, and posts signals to backend.
// ===========================================================
import { fetchTrendingTokens } from "./meme/fetchTrendingTokens.js";
import { predictMemeAlpha } from "./ml/xgbModel.js";
import { postMemeSignalToBackend } from "./backendClient.js";
import fetch from "node-fetch";
import { fetchCombinedSocialSentiment } from "./social.js";
import { collectRealMemeData } from "./data/realDataCollector.js";

//async function fetchTrendingTokens() {
//  const symbols = ["PEPE", "WIF", "BONK", "FLOKI", "DOGE"];
 // return await collectRealMemeData(symbols);
//}

// Loop interval (default: 60 sec)
const MEME_LOOP_MS = Number(process.env.MEME_LOOP_MS || 60_000);

// API endpoints
const DEX_URL = "https://api.dexscreener.com/latest/dex/search?q=";
const PUMPFUN_URL =
  process.env.PUMPFUN_TRENDING_URL || "https://pumpportal.fun/api/trending";
const BITQUERY_URL = process.env.BITQUERY_URL || "https://graphql.bitquery.io";
const BITQUERY_KEY = process.env.BITQUERY_KEY || "";

// -----------------------------------------------------------
// Utility: ratio
// -----------------------------------------------------------
const ratio = (b, s) => {
  const bb = Number(b ?? 0);
  const ss = Number(s ?? 0);
  return bb + ss === 0 ? 0 : (bb - ss) / (bb + ss);
};

// -----------------------------------------------------------
// DexScreener data
// -----------------------------------------------------------
async function fetchDexData(symbol) {
  try {
    const r = await fetch(DEX_URL + encodeURIComponent(symbol));
    if (!r.ok) return null;

    const j = await r.json();
    if (!j?.pairs?.length) return null;
    const p = j.pairs[0];

    return {
      marketcap: Number(p.fdv ?? 0),
      liquidityusd: Number(p.liquidity?.usd ?? 0),
      volumeusd: Number(p.volume?.h24 ?? 0),
      tradecount:
        Number(p.txns?.h24?.buys ?? 0) + Number(p.txns?.h24?.sells ?? 0),
      buys_5m: Number(p.txns?.m5?.buys ?? 0),
      sells_5m: Number(p.txns?.m5?.sells ?? 0),
      age_seconds: Number(p.age ?? 0),
      dex_score: Number(p.score ?? 0),
    };
  } catch (e) {
    console.error("[MEME] Dex data error:", e);
    return null;
  }
}

// -----------------------------------------------------------
// PumpFun Trending
// -----------------------------------------------------------
async function fetchPumpFunTrending() {
  try {
    const r = await fetch(PUMPFUN_URL);
    if (!r.ok) return [];

    const j = await r.json();
    const list = j.trending || j;

    return list.map((c) => ({
      symbol: c.ticker || c.symbol || c.token,
      holders: Number(c.holders ?? 0),
      pumpfun_score: Number(c.score ?? 0),
      age_seconds: Number(c.age_seconds ?? 0),
    }));
  } catch (e) {
    console.error("[MEME] Pumpfun error:", e);
    return [];
  }
}

// -----------------------------------------------------------
// Bitquery "existence" score
// -----------------------------------------------------------
async function fetchBitqueryScore(symbol) {
  if (!BITQUERY_KEY) return 0.1;

  try {
    const body = {
      query: `
        query Score($sym: String!) {
          ethereum {
            address(address: {is: $sym}) {
              annotation
            }
          }
        }
      `,
      variables: { sym: symbol },
    };

    const r = await fetch(BITQUERY_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-KEY": BITQUERY_KEY,
      },
      body: JSON.stringify(body),
    });

    if (!r.ok) return 0.1;

    const d = await r.json();
    const exists = d?.data?.ethereum?.address?.length > 0;

    return exists ? 0.7 : 0.1;
  } catch (err) {
    console.error("[MEME] Bitquery error:", err);
    return 0.1;
  }
}

// -----------------------------------------------------------
// Process one coin → ML inference → signal → backend
// -----------------------------------------------------------
async function processCoin(coin) {
  const symbol = coin.symbol;
  console.log("[MEME] Processing:", symbol);

  const [dex, social, bitScore] = await Promise.all([
    fetchDexData(symbol),
    fetchCombinedSocialSentiment(symbol),
    fetchBitqueryScore(symbol),
  ]);

  if (!dex) {
    console.log("[MEME] Missing Dex data → skip:", symbol);
    return;
  }

  const velocity = ratio(dex.buys_5m, dex.sells_5m);
  const recency = Math.exp(-Number(coin.age_seconds ?? 0) / 3600);
  const social_score = Number(social?.score ?? 0.5);

  // ML  
  const features = {
    recency,
    social_score,
    velocity,
    marketcap: dex.marketcap,
    liquidityusd: dex.liquidityusd,
    volumeusd: dex.volumeusd,
    holders: coin.holders,
    tradecount: dex.tradecount,
    age_seconds: coin.age_seconds,
    buys_5m: dex.buys_5m,
    sells_5m: dex.sells_5m,
    buys_vs_sells_ratio: velocity,
    pumpfun_score: coin.pumpfun_score,
    dex_score: dex.dex_score,
    bitquery_score: bitScore,
  };

  let alpha = await predictMemeAlpha(features);
  if (!Number.isFinite(alpha)) alpha = 0.5;

  let direction = "HOLD";
  if (alpha >= 0.65) direction = "BUY";
  else if (alpha <= 0.35) direction = "SELL";

  const confidence = Math.min(1, Math.abs(alpha - 0.5) * 2);

  if (direction === "HOLD" || confidence < 0.6) {
    console.log("[MEME] Weak → skip:", symbol);
    return;
  }

  // POST TO BACKEND
  await postMemeSignalToBackend({
    symbol,
    trend_score: recency,
    social_score,
    momentum: velocity,
    alpha,
    direction,
    confidence,

    // Pass full metadata for dashboard & ML retraining
    marketcap: dex.marketcap,
    liquidityusd: dex.liquidityusd,
    volumeusd: dex.volumeusd,
    holders: coin.holders,
    tradecount: dex.tradecount,
    age_seconds: dex.age_seconds,
    buys_5m: dex.buys_5m,
    sells_5m: dex.sells_5m,
    buys_vs_sells_ratio: velocity,
    pumpfun_score: coin.pumpfun_score,
    dex_score: dex.dex_score,
    bitquery_score: bitScore,
  });

  console.log(
    `[MEME] Posted ${direction} ${symbol} alpha=${alpha.toFixed(
      3
    )} conf=${(confidence * 100).toFixed(1)}%`
  );
}

// -----------------------------------------------------------
// ONE FULL CYCLE
// -----------------------------------------------------------
export async function runMemeEngineOnce() {
  console.log("[MEME] Fetching trending tokens…");

  const universe = await fetchPumpFunTrending();
  console.log("[MEME] Universe size:", universe.length);

  for (const coin of universe) {
    try {
      await processCoin(coin);
      await new Promise((res) => setTimeout(res, 350)); // anti-rate-limit
    } catch (err) {
      console.error("[MEME] Coin error:", err);
    }
  }
}

// -----------------------------------------------------------
// LOOP
// -----------------------------------------------------------
export function startMemeEngineLoop() {
  console.log(`[MEME] Loop every ${MEME_LOOP_MS / 1000} seconds`);

  async function loop() {
    try {
      await runMemeEngineOnce();
    } catch (err) {
      console.error("[MEME] Loop error:", err);
    } finally {
      setTimeout(loop, MEME_LOOP_MS);
    }
  }

  loop();
}
