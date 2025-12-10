import express from "express";
import {pool} from "../db.js";

const router = express.Router();

/**
 * GET /api/quant/portfolio/:id/latest
 *   → latest quant snapshot for a portfolio
 */
router.get("/portfolio/:id/latest", async (req, res) => {
  const portfolioId = Number(req.params.id);

  try {
    const result = await pool.query(
      `
      SELECT *
      FROM portfolio_quant_metrics
      WHERE portfolio_id = $1
      ORDER BY snapshot_ts DESC
      LIMIT 1;
      `,
      [portfolioId]
    );

    if (!result.rows.length) {
      return res.status(404).json({ error: "no_snapshot" });
    }

    res.json(result.rows[0]);
  } catch (err) {
    console.error("[QUANT] latest fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

/**
 * GET /api/quant/portfolio/:id/history?days=90
 *   → time series of snapshots (for charts)
 */
router.get("/portfolio/:id/history", async (req, res) => {
  const portfolioId = Number(req.params.id);
  const days = Number(req.query.days || 90);

  try {
    const result = await pool.query(
      `
      SELECT *
      FROM portfolio_quant_metrics
      WHERE portfolio_id = $1
        AND snapshot_ts >= now() - ($2::int || ' days')::interval
      ORDER BY snapshot_ts ASC;
      `,
      [portfolioId, days]
    );

    res.json(result.rows);
  } catch (err) {
    console.error("[QUANT] history fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

export default router;
