export function computeAlphaScore({ priceMomentum, sentimentScore, onChainSignal = 0.5, weights }) {
  const { price_momentum_weight, social_sentiment_weight, on_chain_weight } = weights;

  const priceNorm = (priceMomentum + 1) / 2;
  const alpha =
    price_momentum_weight * priceNorm +
    social_sentiment_weight * sentimentScore +
    on_chain_weight * onChainSignal;

  return Math.max(0, Math.min(1, alpha));
}

export function classifyDirection(alphaScore, thresholds) {
  const { strong_buy, buy, hold, sell } = thresholds;

  if (alphaScore >= strong_buy) return "BUY";
  if (alphaScore >= buy) return "BUY";
  if (alphaScore > hold) return "HOLD";
  if (alphaScore > sell) return "SELL";
  return "SELL";
}

export function computeConfidence(alphaScore) {
  const dist = Math.abs(alphaScore - 0.5);
  return Math.max(0, Math.min(1, dist * 2));
}
