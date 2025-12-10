const positiveWords = [
  "bullish",
  "moon",
  "pump",
  "uptrend",
  "accumulate",
  "buy",
  "long",
  "strong",
  "breakout",
  "green",
  "ath"
];

const negativeWords = [
  "bearish",
  "dump",
  "crash",
  "sell",
  "liquidation",
  "short",
  "rekt",
  "panic",
  "rug",
  "down"
];

export function scoreTextSentiment(text) {
  if (!text) return 0.5;
  const lower = text.toLowerCase();
  let score = 0;

  for (const w of positiveWords) {
    if (lower.includes(w)) score += 1;
  }
  for (const w of negativeWords) {
    if (lower.includes(w)) score -= 1;
  }

  if (score > 5) score = 5;
  if (score < -5) score = -5;

  const normalized = (score + 5) / 10;
  return normalized;
}

export function aggregateSentiment(messages) {
  if (!messages || messages.length === 0) return 0.5;

  let weighted = 0;
  let totalWeight = 0;

  for (const msg of messages) {
    const s = scoreTextSentiment(msg.text || "");
    const w = msg.weight ?? 1;
    weighted += s * w;
    totalWeight += w;
  }

  if (totalWeight === 0) return 0.5;
  return weighted / totalWeight;
}
