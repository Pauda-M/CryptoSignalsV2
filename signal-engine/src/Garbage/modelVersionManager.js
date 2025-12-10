import fetch from "node-fetch";
import dotenv from "dotenv";
dotenv.config();

const BACKEND = process.env.BACKEND_URL || "http://localhost:4000";

export async function modelVersionExists(name) {
  const res = await fetch(`${BACKEND}/api/model-versions`);
  if (!res.ok) {
    console.error("[MODEL] Failed to fetch versions:", res.status);
    return false;
  }
  const list = await res.json();
  return list.some((m) => m.name === name);
}

export async function createModelVersion(name, description = null) {
  console.log("[MODEL] Ensuring model version exists (lazy):", name);
  return { name, description };
}
