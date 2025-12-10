const express = require("express");
const router = express.Router();
const db = require("../db"); // Adjust if your pg client path differs

// GET /api/pumpx/history/:mint
router.get("/history/:mint", async (req, res) => {
  const { mint } = req.params;

  try {
    const result = await db.query(
      `
      SELECT
        timestamp,
        price,
        pump_probability
      FROM meme_token_history
      WHERE mint = $1
      ORDER BY timestamp ASC;
      `,
      [mint]
    );

    res.json({ history: result.rows });
  } catch (err) {
    console.error("Error loading history:", err);
    res.status(500).json({ error: "History lookup failed" });
  }
});

module.exports = router;
