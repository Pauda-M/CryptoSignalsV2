// backend-engine/src/routes/pumpxRoutes.js
import express from "express";
import pool from "../db.js";

const router = express.Router();

// ----------------------
// PumpX Radar route
// ----------------------
router.get("/radar", async (req, res) => {
  try {
    const minProb = Number(req.query.minProb || 0);
    const minMcap = Number(req.query.minMcap || 0);
    const minBuys1h = Number(req.query.minBuys1h || 0);
    const minDelta1h = Number(req.query.minDelta1h || 0);

    const sql = `
      SELECT *
      FROM v_pumpx_live
      WHERE pump_probability >= $1
        AND marketcap        >= $2
        AND buys_1h          >= $3
        AND price_change_1h  >= $4
      ORDER BY pump_probability DESC NULLS LAST,
               marketcap        DESC NULLS LAST;
    `;

    const result = await pool.query(sql, [
      minProb,
      minMcap,
      minBuys1h,
      minDelta1h,
    ]);

    res.json({ ok: true, rows: result.rows || [] });
  } catch (err) {
    console.error("[Radar API ERROR]", err);
    res.json({ ok: false, error: err.message, rows: [] });
  }
});

// ----------------------
// PumpX Alerts route
//   → use v_pumpx_signals (latest metrics + prob)
// ----------------------
router.get("/alerts", async (req, res) => {
  try {
    const sql = `
      SELECT *
      FROM v_pumpx_signals
      ORDER BY pump_probability DESC NULLS LAST,
               price_change_1h  DESC NULLS LAST,
               "timestamp"      DESC
      LIMIT 200;
    `;

    const result = await pool.query(sql);
    res.json({ ok: true, rows: result.rows || [] });
  } catch (err) {
    console.error("[Alerts API ERROR]", err);
    res.json({ ok: false, error: err.message, rows: [] });
  }
});

// ----------------------
// PumpX Trends route
//   → use v_pumpx_live_filtered for “top trending” tokens
// ----------------------
router.get("/trends", async (req, res) => {
  try {
    const sql = `
      SELECT *
      FROM v_pumpx_live_filtered
      ORDER BY pump_probability DESC NULLS LAST,
               marketcap        DESC NULLS LAST,
               volume_5m        DESC NULLS LAST
      LIMIT 200;
    `;

    const result = await pool.query(sql);
    res.json({ ok: true, rows: result.rows || [] });
  } catch (err) {
    console.error("[Trends API ERROR]", err);
    res.json({ ok: false, error: err.message, rows: [] });
  }
});

export default router;
