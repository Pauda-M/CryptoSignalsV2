import express from "express";
import {pool} from "../db.js";

const router = express.Router();

router.get("/", async (_req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM timeframes ORDER BY id ASC;"
    );
    res.json(result.rows);
  } catch (err) {
    console.error("[TIMEFRAMES] fetch error:", err);
    res.status(500).json({ error: "db_error" });
  }
});

export default router;
