import pool from "../db.js";

export async function cleanupPumpxHistory() {
  try {
    await pool.query(`
      DELETE FROM meme_token_history
      WHERE "timestamp" < NOW() - INTERVAL '14 days'
    `);
    console.log("[PumpX] Retention cleanup OK");
  } catch (err) {
    console.error("[PumpX] Retention cleanup FAILED:", err);
  }
}
