import {pool} from "./db.js";

const TIMEFRAMES = [
  { name: "1m", label: "1 Minute" },
  { name: "5m", label: "5 Minutes" },
  { name: "15m", label: "15 Minutes" },
  { name: "1h", label: "1 Hour" },
  { name: "4h", label: "4 Hours" },
  { name: "1d", label: "1 Day" }
];

export async function bootstrapDb() {
  console.log("[BOOTSTRAP] Starting DB bootstrap...");
  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    // ASSETS TABLE (for FK in signals)
    await client.query(`
      CREATE TABLE IF NOT EXISTS assets (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL UNIQUE
      );
    `);

    // SIGNALS TABLE (core)
    await client.query(`
      CREATE TABLE IF NOT EXISTS signals (
        id SERIAL PRIMARY KEY,
        asset_id INTEGER REFERENCES assets(id),
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        model_name TEXT NOT NULL,
        direction TEXT NOT NULL,
        confidence DOUBLE PRECISION NOT NULL,
        entry_price DOUBLE PRECISION,
        stop_loss DOUBLE PRECISION,
        take_profit DOUBLE PRECISION,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `);

    // MEME SIGNALS TABLE (extended)
    await client.query(`
      CREATE TABLE IF NOT EXISTS meme_signals (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,

        trend_score DOUBLE PRECISION,
        social_score DOUBLE PRECISION,
        momentum DOUBLE PRECISION,
        alpha DOUBLE PRECISION,

        direction TEXT,
        confidence DOUBLE PRECISION,

        marketcap DOUBLE PRECISION,
        liquidityusd DOUBLE PRECISION,
        volumeusd DOUBLE PRECISION,
        holders INTEGER,
        tradecount INTEGER,
        age_seconds DOUBLE PRECISION,

        buys_5m INTEGER,
        sells_5m INTEGER,
        buys_vs_sells_ratio DOUBLE PRECISION,

        pumpfun_score DOUBLE PRECISION,
        dex_score DOUBLE PRECISION,
        bitquery_score DOUBLE PRECISION,

        model_version_id INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `);

    // TIMEFRAMES with schema self-heal
    const tfCheck = await client.query(`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_name = 'timeframes';
    `);
    const tfCols = tfCheck.rows.map((r) => r.column_name);
    const mustHave = ["id", "name", "label"];
    const mismatch = mustHave.some((c) => !tfCols.includes(c));

    if (mismatch && tfCols.length > 0) {
      console.warn(
        "[BOOTSTRAP] Recreating timeframes table (schema mismatch detected)"
      );
      await client.query(`DROP TABLE IF EXISTS timeframes CASCADE;`);
    }

    await client.query(`
      CREATE TABLE IF NOT EXISTS timeframes (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        label TEXT NOT NULL
      );
    `);

    await client.query(`
      CREATE UNIQUE INDEX IF NOT EXISTS ux_timeframes_name
      ON timeframes(name);
    `);

    // MODEL VERSIONS
    await client.query(`
      CREATE TABLE IF NOT EXISTS model_versions (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        version_tag TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        trained_on_rows INTEGER NOT NULL,
        notes TEXT,
        features JSONB
      );
    `);

    // Seed timeframes
    for (const tf of TIMEFRAMES) {
      await client.query(
        `
        INSERT INTO timeframes (name, label)
        VALUES ($1,$2)
        ON CONFLICT (name) DO UPDATE SET label = EXCLUDED.label;
        `,
        [tf.name, tf.label]
      );
    }

    // Helpful indexes
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_signals_symbol_created
      ON signals(symbol, created_at DESC);
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_meme_signals_symbol_created
      ON meme_signals(symbol, created_at DESC);
    `);

    await client.query("COMMIT");
    console.log("[BOOTSTRAP] DB bootstrap completed.");
  } catch (err) {
    await client.query("ROLLBACK");
    console.error("[BOOTSTRAP] FAILED:", err);
    throw err;
  } finally {
    client.release();
  }
}
