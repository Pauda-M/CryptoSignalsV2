import express from "express";
import {pool} from "../db.js";

const router = express.Router();

router.get("/", async (_req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM model_versions ORDER BY created_at DESC LIMIT 50;"
    );
    res.json(result.rows);
  } catch (err) {
    console.error("[MODELS] fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

router.post("/", async (req, res) => {
  const { name, version_tag, trained_on_rows, notes, features } = req.body || {};

  try {
    const result = await pool.query(
      `
      INSERT INTO model_versions
        (name, version_tag, trained_on_rows, notes, features)
      VALUES ($1,$2,$3,$4,$5)
      RETURNING *;
      `,
      [name, version_tag, trained_on_rows, notes ?? null, features ?? null]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error("[MODELS] insert error:", err);
    res.status(500).json({ error: "insert_failed" });
  }
});

export default router;
