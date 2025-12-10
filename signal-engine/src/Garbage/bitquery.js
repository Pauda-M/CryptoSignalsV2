// bitquery.js - Pump.fun token fundamentals from Bitquery
// ------------------------------------------------------------
// Required: process.env.BITQUERY_API_KEY
// ------------------------------------------------------------

import fetch from "node-fetch";

const BITQUERY_URL = "https://streaming.bitquery.io/eap";

export async function fetchBitqueryPumpFunData(mint) {
  try {
    const query = {
      query: `
        query PumpfunData($token: String!) {
          Solana {
            TokenHolderStats(
              limit: {count: 1}
              where: { mint: { is: $token } }
            ) {
              addressCount
            }
            DEXTrade(
              limit: {count: 50}
              where: { mint: { is: $token } }
            ) {
              count
              tradeAmount
            }
            TokenMetadata(
              limit: {count: 1}
              where: { mint: { is: $token } }
            ) {
              name
              symbol
              decimals
              mintedAt
            }
            TokenMarket(
              limit: {count: 1}
              where: { mint: { is: $token } }
            ) {
              marketCap
              volumeUSD
              liquidityUSD
              price
            }
          }
        }
      `,
      variables: { token: mint },
      mode: "no-cors",
    };

    const res = await fetch(BITQUERY_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-KEY": process.env.BITQUERY_API_KEY || "",
      },
      body: JSON.stringify(query),
    });

    if (!res.ok) {
      console.warn("[BITQUERY] Non-OK:", res.status);
      return null;
    }

    const json = await res.json();

    const d = json?.data?.Solana ?? {};

    const market = d.TokenMarket?.[0] || {};
    const holders = d.TokenHolderStats?.[0]?.addressCount ?? 0;
    const trades = d.DEXTrade?.reduce(
      (acc, t) => {
        acc.count += t.count ?? 0;
        acc.amount += t.tradeAmount ?? 0;
        return acc;
      },
      { count: 0, amount: 0 }
    );

    return {
      marketCap: Number(market.marketCap ?? 0),
      liquidityUSD: Number(market.liquidityUSD ?? 0),
      volumeUSD: Number(market.volumeUSD ?? 0),
      price: Number(market.price ?? 0),
      holders: Number(holders),
      tradeCount: Number(trades.count),
      tradeAmount: Number(trades.amount),
    };
  } catch (err) {
    console.warn("[BITQUERY] Failed:", err.message);
    return null;
  }
}
