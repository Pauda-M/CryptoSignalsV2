import pkg from "pg";
const { Pool } = pkg;

import { MEME_TABLE_SCHEMA } from "./schemas/memeSchema.js";

const pool = new Pool({
  user: process.env.DB_USER || "postgres",
  host: process.env.DB_HOST || "localhost",
  database: process.env.DB_NAME || "crypto_signals",
  password: process.env.DB_PASS || "KarmaKoma2024",
  port: Number(process.env.DB_PORT || 5432),
});

export async function ensureBootstrap() {
  console.log("[BOOTSTRAP] Starting DB bootstrap...");

  try {
    await pool.query(MEME_TABLE_SCHEMA);
    console.log("[BOOTSTRAP] ✓ meme_signals table OK.");

  } catch (err) {
    console.error("[BOOTSTRAP] FAILED:", err.message);
    throw err;
  }
}

export default pool;
