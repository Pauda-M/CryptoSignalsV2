export function normalize(value, max) {
  if (!value || value <= 0) return 0;
  return Math.min(1, value / max);
}

export function scoreMarketCap(mc) {
  // microcaps (<100k) get max boost
  return 1 - normalize(mc, 2_000_000); // decay by $2M
}

export function scoreLiquidity(liq) {
  // sweet spot around $10k - $50k
  if (liq <= 5000) return 0.1;
  if (liq <= 15000) return 0.4;
  return normalize(liq, 50_000);
}

export function scoreVolume(vol) {
  return normalize(vol, 500_000); // 500k daily vol
}

export function scoreHolders(h) {
  return normalize(h, 2000); // early tokens < 2k holders
}

export function scoreTradeCount(c) {
  return normalize(c, 20000);
}

export function scoreVelocity(volume, liquidity) {
  if (liquidity === 0) return 0;
  return normalize(volume / liquidity, 50); // vol/liquidity ratio
}
