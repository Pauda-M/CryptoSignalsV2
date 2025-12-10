module.exports = {
  apps: [


    /* ============================
          PUMPFUN INGEST (python)
          ✔ fixed folder ml/data_ingestion
    ============================ */
    {
      name: "pumpfun-ingest",
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      script: "cmd.exe",
      interpreter: "none",
      args: ["/c", "start-pumpfun-ingest.cmd"],
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
          PUMPX SCORING
    ============================ */
    {
      name: "pumpx-scoring",
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      script: "cmd.exe",
      interpreter: "none",
      args: ["/c", "start-pumpx-scoring.cmd"],
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
          PUMPX SIGNALS
    ============================ */
    {
      name: "pumpx-signals",
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      script: "cmd.exe",
      interpreter: "none",
      args: ["/c", "start-pumpx-signals.cmd"],
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
          PUMPX TREND
    ============================ */
    {
      name: "pumpx-trend",
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      script: "cmd.exe",
      interpreter: "none",
      args: ["/c", "start-pumpx-trend.cmd"],
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
          STREAMER ENGINE (Node)
    ============================ */
    {
      name: "pumpx-streamer",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/pumpx-streamer-engine",
      script: "node",
      interpreter: "none",
      args: ["src/server.js"],
      windowsHide: true,
      autorestart: true,
      restart_delay: 3000
    }
  ]
};
