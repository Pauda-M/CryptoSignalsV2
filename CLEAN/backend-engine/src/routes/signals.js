import express from "express";
import { query } from "../db.js";

export const router = express.Router();

router.get("/", async (_, res) => {
    try {
        const rows = await query(`
            SELECT *
            FROM meme_alpha_signals
            ORDER BY timestamp DESC
            LIMIT 200
        `);
        res.json(rows);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "signals query failed" });
    }
});
export default router;