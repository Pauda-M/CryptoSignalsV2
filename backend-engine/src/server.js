// backend-engine/src/server.js
// Main backend API (port 4000)

import express from "express";
import http from "http";
import cors from "cors";
import { Server as SocketIOServer } from "socket.io";
import dotenv from "dotenv";

import { bootstrapDb } from "./bootstrap.js";

// existing routes
import portfolioRoutes from "./routes/portfolios.js";
import quantRoutes from "./routes/quant.js";
import signalsRoutes from "./routes/signals.js";
import memeSignalRoutes from "./routes/memeSignals.js";
import timeframeRoutes from "./routes/timeframes.js";

// ⭐ NEW PumpX routes
import pumpxRoutes from "./routes/pumpxRoutes.js";

// ---------------------------------------------------------------------

dotenv.config();
const app = express();
const server = http.createServer(app);

const PORT = process.env.PORT || 4000;

// CORS + JSON
app.use(
  cors({
    origin: "*",
  })
);
app.use(express.json());

// ---------------------------------------------------------------------
// Attach your existing API routes
// ---------------------------------------------------------------------

app.use("/api/portfolios", portfolioRoutes);
app.use("/api/quant", quantRoutes);
app.use("/api/signals", signalsRoutes);
app.use("/api/meme", memeSignalRoutes);
app.use("/api/timeframes", timeframeRoutes);

// ⭐ NEW PumpX API
app.use("/api/pumpx", pumpxRoutes);

// ---------------------------------------------------------------------
// No PumpX Streamer here!
// (You run pumpx-streamer-engine on port 4101 via PM2)
// ---------------------------------------------------------------------

// Root status
app.get("/", (req, res) => {
  res.json({ status: "Pauda Backend OK" });
});

// ---------------------------------------------------------------------

(async () => {
  try {
    await bootstrapDb();

    server.listen(PORT, () => {
      console.log("==============================================");
      console.log("      CRYPTO SIGNALS PAUDA BACKEND v5");
      console.log("==============================================");
      console.log(`REST API running on http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error("[SERVER] Fatal bootstrap error:", err);
    process.exit(1);
  }
})();
