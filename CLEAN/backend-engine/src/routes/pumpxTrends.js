import express from "express";
import pool from "../db.js";

const router = express.Router();

// Latest 6-hour trends
router.get("/trends", async (req, res) => {
  try {
    const { rows } = await pool.query(`
      SELECT *
      FROM pumpx_trends
      ORDER BY score DESC
      LIMIT 200;
    `);

    res.json(rows);
  } catch (err) {
    console.error("[PumpX] trends error:", err);
    res.status(500).json({ error: "Failed to load trends" });
  }
});

export default router;
