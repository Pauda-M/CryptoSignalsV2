import fetch from "node-fetch";
import dotenv from "dotenv";

dotenv.config();

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:4000";

export async function fetchCombinedSocialSentiment(symbol) {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/sentiment/global?symbol=${encodeURIComponent(symbol)}`
    );
    if (!res.ok) return { score: 0.5 };
    return res.json();
  } catch (err) {
    console.warn("[SOCIAL] fetch failed:", err.message);
    return { score: 0.5 };
  }
}
