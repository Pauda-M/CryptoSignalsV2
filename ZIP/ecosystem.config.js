module.exports = {
  apps: [
    /* ============================
       BACKEND (npm run dev)
    ============================ */
{
  name: "Backend-Server",
  cwd: "C:/CryptoTrader/next_version/crypto-signals/backend-engine",
  script: "cmd.exe",
  interpreter: "none",
  windowsHide: true,
  args: [ "/c", "start-backend.cmd" ],
  autorestart: true,
  restart_delay: 2000
},

    /* ============================
       FRONTEND (PowerShell + Vite)
    ============================ */
{
  name: "Frontend-Server",
  cwd: "C:/CryptoTrader/next_version/crypto-signals/frontend-engine",
  script: "cmd.exe",
  interpreter: "none",
  windowsHide: true,
  args: [ "/c", "start-frontend.cmd" ],
  autorestart: true,
  restart_delay: 2000,
  watch:true,
  Revision: "N@xtv1.1"
  
},
    /* ============================
       PUMPFUN INGEST (pythonw)
    ============================ */
    {
      name: "pumpfun-ingest",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/ml/",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/.venv-ml/Scripts/activate.bat",
      args: "data_ingestion/ingest_pumpfun_live.py",
      interpreter: "pythonw.exe",
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
       PUMPX SCORING LOOP (pythonw)
    ============================ */
    {
      name: "pumpx-scoring",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/.venv-ml/Scripts/pythonw.exe",
      args: "ml/pumpx_scoring_loop.py",
      interpreter: "none",
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
       PUMPX TREND ENGINE (pythonw)
    ============================ */
    {
      name: "pumpx-trend",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/.venv-ml/Scripts/pythonw.exe",
      args: "ml/pumpx_trend_engine.py",
      interpreter: "none",
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
       PUMPX SIGNAL ENGINE (pythonw)
    ============================ */
    {
      name: "pumpx-signals",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/.venv-ml/Scripts/pythonw.exe",
      args: "ml/pumpx_signal_engine.py",
      interpreter: "none",
      windowsHide: true,
      autorestart: true,
      restart_delay: 5000
    },

    /* ============================
       PUMPX STREAMER (Node)
    ============================ */
    {
      name: "pumpx-streamer",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/pumpx-streamer-engine",
      script: "node",
      interpreter: "none",
      args: "src/server.js",
      windowsHide: true,
      autorestart: true,
      restart_delay: 3000
    },
{
  name: "pumpx-signals-Marko",
  cwd: "C:\CryptoTrader\next_version\crypto-signals",
  script: "cmd.exe",
  interpreter: "none",
  args: [ "/c", "start-pumpx-signal-marko.cmd" ],
  windowsHide: true,
  autorestart: true,
  restart_delay: 3000
}
  ]
};
