import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

const BACKEND = process.env.BACKEND_URL || "http://localhost:4000";

export async function timeframeExists(code) {
  const res = await fetch(`${BACKEND}/api/timeframes`);
  if (!res.ok) {
    console.error("[TIMEFRAMES] Failed to fetch list:", res.status);
    return false;
  }
  const list = await res.json();
  return list.some((t) => t.code === code);
}

export async function createTimeframe(code) {
  const minutes = code.endsWith("m")
    ? parseInt(code, 10)
    : code.endsWith("h")
    ? parseInt(code, 10) * 60
    : code.endsWith("d")
    ? parseInt(code, 10) * 1440
    : 15;

  const payload = { code, granularity_minutes: minutes };

  console.log("[TIMEFRAMES] Creating timeframe", code);

  const res = await fetch(`${BACKEND}/api/timeframes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const text = await res.text();
    console.error("[TIMEFRAMES] Create failed:", text);
    throw new Error("Timeframe creation failed");
  }

  return await res.json();
}
