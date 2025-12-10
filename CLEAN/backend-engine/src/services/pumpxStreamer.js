import EventEmitter from "events";
import pkg from "pg";
const { Pool } = pkg;

class PumpXStreamer extends EventEmitter {
  constructor() {
    super();

    this.pool = new Pool({
      host: process.env.PGHOST || "localhost",
      port: process.env.PGPORT || 5432,
      user: process.env.PGUSER || "postgres",
      password: process.env.PGPASSWORD || "",
      database: process.env.PGDATABASE || "crypto_signals",
    });

    this.isRunning = false;
  }

  async start() {
    if (this.isRunning) return;
    this.isRunning = true;

    console.log("[PumpXStreamer] Started.");

    const loop = async () => {
      try {
        const result = await this.pool.query(`
          SELECT *
          FROM v_pumpx_live
          ORDER BY pump_probability DESC NULLS LAST
          LIMIT 200;
        `);

        // Emit update event for server.js
        this.emit("update", result.rows);
      } catch (err) {
        console.error("[PumpXStreamer] ERROR:", err.message);
      }

      setTimeout(loop, 5000);
    };

    loop();
  }
}

const instance = new PumpXStreamer();

// Default export (IMPORTANT!)
export default instance;
