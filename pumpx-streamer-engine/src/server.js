/**
 * PumpX Streamer — WebSocket Server
 * Streams:
 *   - pumpx_snapshot  (full dataset)
 *   - pumpx_alerts    (alerts when changed)
 */

import express from "express";
import http from "http";
import cors from "cors";
import { Server } from "socket.io";
import pkg from "pg";
const { Client } = pkg;

import generatePumpAlerts from "./alerts.js";

const PORT = 4101;

// -------------------------------
// PostgreSQL connection
// -------------------------------
const db = new Client({
  host: process.env.PGHOST || "localhost",
  port: process.env.PGPORT || 5432,
  user: process.env.PGUSER || "postgres",
  password: process.env.PGPASSWORD || "postgres",
  database: process.env.PGDATABASE || "crypto_signals",
});

db.connect()
  .then(() => console.log("[PumpXStreamer] Connected to PostgreSQL"))
  .catch((err) => console.error("[PumpXStreamer] PostgreSQL error:", err));

// -------------------------------
// Express + WebSocket server
// -------------------------------
const app = express();
app.use(cors());

const httpServer = http.createServer(app);

const io = new Server(httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
  },
});

// -------------------------------
// INTERNAL STATE FOR "OPTION D"
// -------------------------------
//
// Store last alert state per token.
// Format:
// {
//     "mint1": { ...alertObj },
//     "mint2": { ...alertObj }
// }
// -------------------------------
const lastAlertsByMint = {};


// -------------------------------
// Streaming Loop
// -------------------------------
async function streamPumpX() {
  try {
    const result = await db.query(`SELECT * FROM v_pumpx_live ORDER BY token_id ASC`);
    const rows = result.rows || [];

    // Emit snapshot
    io.emit("pumpx_snapshot", rows);
    console.log(`[PumpXStreamer] Emitted snapshot with ${rows.length} rows`);

    // Generate alerts
    const alerts = generatePumpAlerts(rows);
    const changedAlerts = [];

    for (const alert of alerts) {
      // Replace alert ID with stable unique ID (mint)
      alert.id = alert.mint;

      const prev = lastAlertsByMint[alert.mint];

      const prevStr = prev ? JSON.stringify(prev) : null;
      const currStr = JSON.stringify(alert);

      // Only emit if alert changed
      if (currStr !== prevStr) {
        changedAlerts.push(alert);
        lastAlertsByMint[alert.mint] = alert; // update state
      }
    }

    if (changedAlerts.length > 0) {
      io.emit("pumpx_alerts", changedAlerts);
      console.log(`[PumpXStreamer] Emitted changed alerts: ${changedAlerts.length}`);

      console.log("ALERT DEBUG:", JSON.stringify(changedAlerts, null, 2));
    } else {
      console.log("[PumpXStreamer] No alert changes");
    }

  } catch (err) {
    console.error("[PumpXStreamer] Streaming error:", err);
  }
}


// -------------------------------
// Main Loop
// -------------------------------
setInterval(streamPumpX, 5000); // Every 5 seconds


// -------------------------------
// Start server
// -------------------------------
httpServer.listen(PORT, () => {
  console.log("==============================================");
  console.log(" PUMPX STREAMER (v_pumpx_live → WebSocket)");
  console.log("==============================================");
  console.log(`Listening on http://localhost:${PORT}`);
});
