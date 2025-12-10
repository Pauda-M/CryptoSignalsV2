import express from "express";
import pool from "../db.js";

const router = express.Router();

// 1. Fetch hourly candles for one mint
router.get("/hourly/:mint", async (req, res) => {
  try {
    const { mint } = req.params;
    const { rows } = await pool.query(
      `
      SELECT *
      FROM pumpx_hourly
      WHERE mint = $1
      ORDER BY hour_bucket ASC
      `,
      [mint]
    );
    res.json(rows);
  } catch (err) {
    console.error("[PumpX] hourly error:", err);
    res.status(500).json({ error: "Failed to load hourly" });
  }
});

export default router;
