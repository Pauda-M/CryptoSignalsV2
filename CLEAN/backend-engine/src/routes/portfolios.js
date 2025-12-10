import express from "express";
import {pool} from "../db.js";

const router = express.Router();

/**
 * Ensure a portfolio exists for a given owner + name.
 * No ON CONFLICT. Uses SELECT → INSERT with unique-ish logic.
 */
async function ensurePortfolio(ownerTelegram, name, baseCurrency = "USD") {
  // 1) Try to find existing
  const existing = await pool.query(
    `
    SELECT id
    FROM portfolios
    WHERE owner_telegram = $1 AND name = $2
    LIMIT 1;
    `,
    [ownerTelegram, name]
  );

  if (existing.rows.length) {
    return existing.rows[0].id;
  }

  // 2) Insert new
  const inserted = await pool.query(
    `
    INSERT INTO portfolios (owner_telegram, name, base_currency)
    VALUES ($1, $2, $3)
    RETURNING id;
    `,
    [ownerTelegram, name, baseCurrency]
  );

  return inserted.rows[0].id;
}

/**
 * Ensure there is an assets row for a symbol, reusing your
 * conflict-safe pattern (SELECT → INSERT → retry on 23505).
 */
async function ensureAssetId(symbol) {
  const existing = await pool.query(
    "SELECT id FROM assets WHERE symbol = $1 LIMIT 1;",
    [symbol]
  );
  if (existing.rows.length) return existing.rows[0].id;

  try {
    const inserted = await pool.query(
      `
      INSERT INTO assets (symbol, name)
      VALUES ($1, $1)
      RETURNING id;
      `,
      [symbol]
    );
    return inserted.rows[0].id;
  } catch (err) {
    if (err.code === "23505") {
      const retry = await pool.query(
        "SELECT id FROM assets WHERE symbol = $1 LIMIT 1;",
        [symbol]
      );
      if (retry.rows.length) return retry.rows[0].id;
    }
    throw err;
  }
}

/**
 * GET /api/portfolios
 * Optional query:
 *   ?owner=telegramId
 */
router.get("/", async (req, res) => {
  const { owner } = req.query;

  try {
    let rows;
    if (owner) {
      const result = await pool.query(
        `
        SELECT *
        FROM portfolios
        WHERE owner_telegram = $1
        ORDER BY created_at DESC;
        `,
        [owner]
      );
      rows = result.rows;
    } else {
      const result = await pool.query(
        `
        SELECT *
        FROM portfolios
        ORDER BY created_at DESC
        LIMIT 100;
        `
      );
      rows = result.rows;
    }

    res.json(rows);
  } catch (err) {
    console.error("[PORTFOLIOS] fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

/**
 * GET /api/portfolios/:id
 * Returns portfolio + positions.
 */
router.get("/:id", async (req, res) => {
  const id = Number(req.params.id);

  try {
    const pRes = await pool.query(
      "SELECT * FROM portfolios WHERE id = $1;",
      [id]
    );
    if (!pRes.rows.length) {
      return res.status(404).json({ error: "not_found" });
    }

    const posRes = await pool.query(
      `
      SELECT *
      FROM portfolio_positions
      WHERE portfolio_id = $1
      ORDER BY symbol;
      `,
      [id]
    );

    res.json({
      portfolio: pRes.rows[0],
      positions: posRes.rows
    });
  } catch (err) {
    console.error("[PORTFOLIOS] detail fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

/**
 * POST /api/portfolios
 * Body example:
 * {
 *   "owner_telegram": "123456789",
 *   "name": "Main Book",
 *   "base_currency": "USD",
 *   "positions": [
 *      {"symbol":"BTCUSDT","quantity":0.5,"avg_entry_price":42000},
 *      {"symbol":"ETHUSDT","quantity":5}
 *   ]
 * }
 */
router.post("/", async (req, res) => {
  const {
    owner_telegram,
    name,
    base_currency = "USD",
    positions = []
  } = req.body || {};

  if (!name) {
    return res.status(400).json({ error: "name_required" });
  }

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    const portfolioId = await ensurePortfolio(
      owner_telegram || null,
      name,
      base_currency
    );

    // wipe old positions for this portfolio (simple approach)
    await client.query(
      "DELETE FROM portfolio_positions WHERE portfolio_id = $1;",
      [portfolioId]
    );

    for (const pos of positions) {
      if (!pos.symbol || !pos.quantity) continue;

      const assetId = await ensureAssetId(pos.symbol);

      await client.query(
        `
        INSERT INTO portfolio_positions (
          portfolio_id,
          asset_id,
          symbol,
          quantity,
          avg_entry_price
        )
        VALUES ($1,$2,$3,$4,$5);
        `,
        [
          portfolioId,
          assetId,
          pos.symbol,
          Number(pos.quantity),
          pos.avg_entry_price != null ? Number(pos.avg_entry_price) : null
        ]
      );
    }

    await client.query("COMMIT");

    res.json({ id: portfolioId });
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("[PORTFOLIOS] insert error:", err);
    res.status(500).json({ error: "insert_failed" });
  } finally {
    client.release();
  }
});

export default router;
