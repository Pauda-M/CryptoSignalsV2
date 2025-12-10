import express from "express";
import {pool} from "../db.js";

const router = express.Router();

// GET for dashboard
router.get("/", async (req, res) => {
  const minConf = Number(req.query.min_conf ?? 0);
  const limit = Number(req.query.limit ?? 200);

  const q = {
    text: `
      SELECT *
      FROM meme_signals
      WHERE confidence IS NULL OR confidence >= $1
      ORDER BY created_at DESC
      LIMIT $2;
    `,
    values: [minConf, limit]
  };

  try {
    const result = await pool.query(q);
    res.json(result.rows);
  } catch (err) {
    console.error("[MEME] fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

// POST from meme engine
router.post("/", async (req, res) => {
  const p = req.body || {};

  const q = {
    text: `
      INSERT INTO meme_signals (
        symbol,
        trend_score,
        social_score,
        momentum,
        alpha,
        direction,
        confidence,
        marketcap,
        liquidityusd,
        volumeusd,
        holders,
        tradecount,
        age_seconds,
        buys_5m,
        sells_5m,
        buys_vs_sells_ratio,
        pumpfun_score,
        dex_score,
        bitquery_score,
        model_version_id
      )
      VALUES (
        $1,$2,$3,$4,
        $5,$6,$7,
        $8,$9,$10,$11,
        $12,$13,$14,$15,
        $16,$17,$18,$19,
        $20
      )
      RETURNING *;
    `,
    values: [
      p.symbol,
      p.trend_score,
      p.social_score,
      p.momentum,
      p.alpha,
      p.direction,
      p.confidence,
      p.marketcap ?? null,
      p.liquidityusd ?? null,
      p.volumeusd ?? null,
      p.holders ?? null,
      p.tradecount ?? null,
      p.age_seconds ?? null,
      p.buys_5m ?? null,
      p.sells_5m ?? null,
      p.buys_vs_sells_ratio ?? null,
      p.pumpfun_score ?? null,
      p.dex_score ?? null,
      p.bitquery_score ?? null,
      p.model_version_id ?? null
    ]
  };

  try {
    const result = await pool.query(q);
    res.json(result.rows[0]);
  } catch (err) {
    console.error("[MEME] insert error:", err);
    res.status(500).json({ error: "insert_failed" });
  }
});

export default router;
