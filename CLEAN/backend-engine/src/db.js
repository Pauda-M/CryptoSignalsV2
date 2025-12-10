import pkg from "pg";
const { Pool } = pkg;

export const pool = new Pool({
    host: process.env.PG_HOST || "pbcryptodb01",
    port: process.env.PG_PORT || 5432,
    user: process.env.PG_USER || "postgres",
    password: process.env.PG_PASSWORD || "KarmaKoma2024",
    database: process.env.PG_DATABASE || "crypto_signals",
});

export async function query(text, params) {
    const res = await pool.query(text, params);
    return res.rows;
}
