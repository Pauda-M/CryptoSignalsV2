import express from "express";

const router = express.Router();

// /api/sentiment/global?symbol=XXX
router.get("/global", (req, res) => {
  const symbol = req.query.symbol || "UNKNOWN";
  res.json({
    symbol,
    score: 0.5 // neutral placeholder until you wire real social data
  });
});

export default router;
