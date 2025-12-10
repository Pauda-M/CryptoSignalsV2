// pumpx-streamer/src/server.js
import express from "express";
import http from "http";
import cors from "cors";
import { Server as SocketIOServer } from "socket.io";
import dotenv from "dotenv";
import pkg from "pg";

dotenv.config();

const { Pool } = pkg;

// DB connection
const pool = new Pool({
  host: process.env.PGHOST || "localhost",
  port: process.env.PGPORT ? Number(process.env.PGPORT) : 5432,
  user: process.env.PGUSER || "postgres",
  password: process.env.PGPASSWORD || "KarmaKoma2024",
  database: process.env.PGDATABASE || "crypto_signals",
});

// config
const PORT = process.env.PUMPX_STREAMER_PORT || 4101;
const BROADCAST_INTERVAL_MS = 5000;
const ALERT_PROB_THRESHOLD = process.env.PUMPX_ALERT_PROB
  ? Number(process.env.PUMPX_ALERT_PROB)
  : 0.85;

const ALERT_STATE_EXPIRATION_MS = 30 * 60 * 1000; // 30 minutes

const app = express();
const server = http.createServer(app);
const io = new SocketIOServer(server, { cors: { origin: "*" } });

app.use(cors());

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "pumpx-streamer" });
});

// --- state to avoid spamming unchanged data / alerts ---
let lastSnapshot = [];
let lastSnapshotHash = "";

// token_id → { isHigh, ts }
const lastAlertState = new Map();

/**
 * Stable hash of important fields (don't hash updated_at!)
 */
function hashRows(rows) {
  const key = rows.map((r) => [
    r.token_id,
    r.price,
    r.pump_probability,
    r.marketcap,
  ]);
  return JSON.stringify(key);
}

/**
 * Remove old alert states (token left top list long ago)
 */
function cleanupAlertState() {
  const now = Date.now();
  for (const [tokenId, info] of lastAlertState.entries()) {
    if (now - info.ts > ALERT_STATE_EXPIRATION_MS) {
      lastAlertState.delete(tokenId);
    }
  }
}

/**
 * Main polling + broadcast loop
 */
async function loopBroadcast() {
  try {
    const { rows } = await pool.query(`
      SELECT *
      FROM v_pumpx_live
      ORDER BY pump_probability DESC NULLS LAST, marketcap DESC
      LIMIT 2000;
    `);

    const snapshotHash = hashRows(rows);

    if (snapshotHash !== lastSnapshotHash) {
      lastSnapshotHash = snapshotHash;
      lastSnapshot = rows;

      console.log(
        "[PumpXStreamer] Emitted snapshot with",
        rows.length,
        "rows"
      );

      io.to("pumpx-subscribers").emit("pumpx_snapshot", rows);
    }

    // ---------------- ALERT LOGIC ----------------
    const newAlerts = [];
    const now = Date.now();

    // track which tokens are present to avoid keeping stale state
    const currentTokenIds = new Set(rows.map((r) => r.token_id));

    for (const row of rows) {
      const tokenId = row.token_id;
      const prob = row.pump_probability ?? 0;

      const entry = lastAlertState.get(tokenId) || { isHigh: false, ts: now };
      const wasHigh = entry.isHigh;
      const isHigh = prob >= ALERT_PROB_THRESHOLD;

      // rising edge
      if (isHigh && !wasHigh) {
        newAlerts.push(row);
      }

      // update state
      lastAlertState.set(tokenId, { isHigh, ts: now });
    }

    // drop tokens no longer in list
    for (const tokenId of lastAlertState.keys()) {
      if (!currentTokenIds.has(tokenId)) {
        lastAlertState.delete(tokenId);
      }
    }

    cleanupAlertState();

    if (newAlerts.length > 0) {
      console.log("[PumpXStreamer] Emitted alerts:", newAlerts.length);
      io.to("pumpx-subscribers").emit("pumpx_alerts", newAlerts);
    }
  } catch (err) {
    console.error("[PumpXStreamer] Error in broadcast loop:", err);
  } finally {
    setTimeout(loopBroadcast, BROADCAST_INTERVAL_MS);
  }
}

// --- WebSocket wiring ---
io.on("connection", (socket) => {
  console.log("[PumpXStreamer] client connected:", socket.id);

  socket.join("pumpx-subscribers");

  if (lastSnapshot.length > 0) {
    socket.emit("pumpx_snapshot", lastSnapshot);
  }

  socket.on("disconnect", () => {
    console.log("[PumpXStreamer] client disconnected:", socket.id);
  });
});

// start server
server.listen(PORT, () => {
  console.log("==============================================");
  console.log("  PUMPX STREAMER (v_pumpx_live → WebSocket)");
  console.log("==============================================");
  console.log(`Listening on http://localhost:${PORT}`);
  loopBroadcast();
});
