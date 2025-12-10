import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";
import { fetchKlines, computePriceMomentum } from "../src/market.js";
import { fetchCombinedSocialSentiment } from "../src/social.js";
import { computeAlphaScore, classifyDirection, computeConfidence } from "../src/alpha.js";
import { assetExists, createAsset } from "../src/assetManager.js";
import { timeframeExists, createTimeframe } from "../src/timeframeManager.js";
import { modelVersionExists, createModelVersion } from "../src/modelVersionManager.js";
import { postSignalToBackend, postMemeSignal } from "../src/backendClient.js";
import { generateMemeSignalsForUniverse } from "../src/memeEngine.js";
import type { CoreSignalPayload, MemeSignalPayload } from "./types.js";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const configPath = path.join(__dirname, "..", "engine-config.json");
const engineConfig = JSON.parse(fs.readFileSync(configPath, "utf-8"));

async function ensureAsset(symbol: string): Promise<void> {
  if (!(await assetExists(symbol))) {
    await createAsset(symbol);
  }
}

async function buildCoreSignal(symbol: string): Promise<CoreSignalPayload> {
  const tf: string = engineConfig.market.interval;
  const limit: number = engineConfig.market.klines_limit;

  await ensureAsset(symbol);

  const candles = await fetchKlines(symbol, tf, limit);
  const momentum = computePriceMomentum(candles, 50);
  const last = candles[candles.length - 1];

  const social = await fetchCombinedSocialSentiment();
  const sentimentScore = social.sentimentScore as number;
  const onChainScore = 0.5;

  const alpha = computeAlphaScore({
    priceMomentum: momentum,
    sentimentScore,
    onChainSignal: onChainScore,
    weights: engineConfig.alpha_logic
  });

  const direction = classifyDirection(alpha, engineConfig.alpha_logic.direction_thresholds);
  const confidence = computeConfidence(alpha);

  const entry: number = last.close;
  const atrLike: number = (last.high - last.low) || entry * 0.005;

  const stopLoss =
    direction === "BUY" ? entry - 1.5 * atrLike : entry + 1.5 * atrLike;
  const takeProfit =
    direction === "BUY" ? entry + 3 * atrLike : entry - 3 * atrLike;

  return {
    symbol,
    timeframe: tf,
    model_name: engineConfig.engine_name,
    direction,
    confidence: Number(confidence.toFixed(4)),
    entry_price: Number(entry.toFixed(2)),
    stop_loss: Number(stopLoss.toFixed(2)),
    take_profit: Number(takeProfit.toFixed(2)),
    price_momentum: Number(momentum.toFixed(4)),
    sentiment_score: Number(sentimentScore.toFixed(4)),
    on_chain_score: Number(onChainScore.toFixed(4)),
    alpha_score: Number(alpha.toFixed(4))
  };
}

async function runCoreSignalsCycle(): Promise<void> {
  for (const symbol of engineConfig.symbols as string[]) {
    const payload = await buildCoreSignal(symbol);
    await postSignalToBackend(payload as unknown as CoreSignalPayload);
  }
}

async function runMemeSignalsCycle(): Promise<void> {
  const universe: string[] = engineConfig.meme?.universe || [];
  if (universe.length === 0) return;

  const signals = await generateMemeSignalsForUniverse(universe, engineConfig.alpha_logic);
  for (const s of signals as MemeSignalPayload[]) {
    await postMemeSignal(s);
  }
}

async function mainLoop(): Promise<void> {
  const intervalMs =
    (engineConfig.loop?.poll_interval_seconds || 60) * 1000;

  await runCoreSignalsCycle();
  await runMemeSignalsCycle();

  setInterval(async () => {
    await runCoreSignalsCycle();
    await runMemeSignalsCycle();
  }, intervalMs);
}

mainLoop().catch((err) => {
  console.error("[ENGINE-TS] Fatal:", err);
  process.exit(1);
});
