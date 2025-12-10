// src/services/pumpxHistory.js
import { pool } from "../db/pool.js"; // adjust to your pool file

export async function getLastHourMessages(limit = 1000) {
  const query = `
    SELECT data
    FROM pumpx_stream
    WHERE updated_at >= NOW() - INTERVAL '1 hour'
    ORDER BY updated_at ASC
    LIMIT $1
  `;
  const { rows } = await pool.query(query, [limit]);
  return rows.map(r => r.data);
}
