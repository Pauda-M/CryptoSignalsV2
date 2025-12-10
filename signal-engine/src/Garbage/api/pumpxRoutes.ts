import express from "express";
import { Pool } from "pg";

const router = express.Router();

const pool = new Pool({
  host: "localhost",
  port: 5432,
  user: "postgres",
  password: "KarmaKoma2024",
  database: "crypto_signals",
});
// ----------------------------------------------------------
// Gainers: tokens with biggest 3-minute price increase
// ----------------------------------------------------------
router.get("/pumpx/gainers", async (req, res) => {
  try {
    const result = await pool.query(
      `
      WITH recent AS (
        SELECT token_id, price, timestamp,
               LAG(price, 3) OVER (PARTITION BY token_id ORDER BY timestamp)
                  AS price_3m_ago
        FROM meme_token_metrics
      )
      SELECT
        t.token_id,
        t.mint,
        t.symbol,
        r.price,
        r.price_3m_ago,
        ((r.price - r.price_3m_ago) / r.price_3m_ago) AS pct_gain
      FROM recent r
      JOIN meme_tokens t ON t.token_id = r.token_id
      WHERE r.price_3m_ago IS NOT NULL
      ORDER BY pct_gain DESC
      LIMIT 30
      `
    );
	// ----------------------------------------------------------
// RISK: liquidity volatility (stddev of liquidity / mean)
// ----------------------------------------------------------
router.get("/pumpx/risk", async (_req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT
        t.token_id,
        t.mint,
        t.symbol,
        STDDEV(m.liquidity) / NULLIF(AVG(m.liquidity),0) AS risk_score,
        COUNT(*) AS samples
      FROM meme_token_metrics m
      JOIN meme_tokens t ON t.token_id = m.token_id
      WHERE m.liquidity IS NOT NULL
      GROUP BY t.token_id, t.mint, t.symbol
      HAVING COUNT(*) > 10
      ORDER BY risk_score DESC
      LIMIT 50
      `
    );

    res.json(result.rows);
  } catch (err) {
    console.error("[PumpX] /pumpx/risk error:", err);
    res.status(500).json({ error: "internal_error" });
  }
});


    res.json(result.rows);
  } catch (err) {
    console.error("[PumpX] /pumpx/gainers error:", err);
    res.status(500).json({ error: "internal_error" });
  }
});

// Top PumpX signals (for dashboard list)
router.get("/pumpx/top", async (req, res) => {
  try {
    const limit = Number(req.query.limit ?? 50);
    const result = await pool.query(
      `
      SELECT *
      FROM v_pumpx_signals
      ORDER BY pump_probability DESC NULLS LAST,
               volume_5m DESC NULLS LAST
      LIMIT $1
      `,
      [limit]
    );
    res.json(result.rows);
  } catch (err) {
    console.error("[API] /pumpx/top error:", err);
    res.status(500).json({ error: "internal_error" });
  }
});

// Detail for a single token by mint
router.get("/pumpx/token/:mint", async (req, res) => {
  try {
    const { mint } = req.params;
    const result = await pool.query(
      `
      SELECT *
      FROM v_pumpx_signals
      WHERE mint = $1
      `,
      [mint]
    );
    if (result.rows.length === 0) {
      res.status(404).json({ error: "not_found" });
      return;
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error("[API] /pumpx/token error:", err);
    res.status(500).json({ error: "internal_error" });
  }
});

// Simple health check
router.get("/pumpx/health", async (_req, res) => {
  try {
    const r = await pool.query("SELECT NOW() as now LIMIT 1;");
    res.json({ ok: true, db_time: r.rows[0].now });
  } catch (err) {
    console.error("[API] /pumpx/health error:", err);
    res.status(500).json({ ok: false });
  }
});

export default router;
