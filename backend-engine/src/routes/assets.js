import express from "express";
import { query } from "../db.js";

export const router = express.Router();

router.get("/", async (_, res) => {
    try {
        const rows = await query(`SELECT * FROM meme_tokens ORDER BY token_id ASC`);
        res.json(rows);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "assets query failed" });
    }
});
export default router;