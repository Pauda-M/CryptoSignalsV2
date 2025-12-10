import fetch from "node-fetch";
import dotenv from "dotenv";

dotenv.config();

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:4000";

async function postJson(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Backend ${path} failed: ${res.status} ${text}`);
  }
  return JSON.parse(text || "{}");
}

export async function postCoreSignalToBackend(payload) {
  return postJson("/api/signals", payload);
}

export async function postMemeSignalToBackend(payload) {
  return postJson("/api/meme-signals", payload);
}
