import ort from "onnxruntime-node";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const FEATURE_ORDER = [
  "recency",
  "social_score",
  "velocity",
  "marketcap",
  "liquidityusd",
  "volumeusd",
  "holders",
  "tradecount",
  "age_seconds",
  "buys_5m",
  "sells_5m",
  "buys_vs_sells_ratio",
  "pumpfun_score",
  "dex_score",
  "bitquery_score"
];

const DEFAULT_MODEL_PATH = path.join(__dirname, "..", "ml_models", "meme_gb.onnx");
const MODEL_PATH = process.env.MEME_MODEL_PATH || DEFAULT_MODEL_PATH;

let sessionPromise = null;

async function getSession() {
  if (!sessionPromise) {
    console.log("[ML] Loading ONNX model from:", MODEL_PATH);
    sessionPromise = ort.InferenceSession.create(MODEL_PATH).catch((err) => {
      console.error("[ML] Failed to load ONNX:", err.message);
      return null;
    });
  }
  return sessionPromise;
}

export async function predictMemeAlpha(features) {
  const session = await getSession();
  if (!session) return NaN;

  try {
    const arr = Float32Array.from(
      FEATURE_ORDER.map((k) => Number(features[k] ?? 0))
    );
    const tensor = new ort.Tensor("float32", arr, [1, FEATURE_ORDER.length]);
    const outputs = await session.run({ input: tensor });
    const key = Object.keys(outputs)[0];
    const raw = outputs[key].data[0];
    if (!Number.isFinite(raw)) return NaN;
    return 1 / (1 + Math.exp(-raw)); // logistic to 0–1
  } catch (err) {
    console.error("[ML] predictMemeAlpha error:", err.message);
    return NaN;
  }
}
