module.exports = {
  apps: [
    /* ----------------------- PYTHON ML ENGINES ----------------------- */
    {
      name: "ML-Scoring-loop",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/pumpx_scoring_loop.py",
      interpreter: "C:/CryptoTrader/next_version/crypto-signals/.venv-ml/Scripts/pythonw.exe",
      windowsHide: true,
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      autorestart: true,
      max_restarts: 20,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx_scoring_loop-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx_predictor.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
	{
      name: "ML-Predictions",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/pumpx_predictor.py",
      interpreter: "C:/CryptoTrader/next_version/crypto-signals/.venv-ml/Scripts/pythonw.exe",
      windowsHide: true,
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      autorestart: true,
      max_restarts: 20,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx_predictor-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx_predictor.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
	{
      name: "pumpx-signals",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/pumpx_signal_engine.py",
      interpreter: "C:/CryptoTrader/next_version/crypto-signals/.venv-ml/Scripts/pythonw.exe",
      windowsHide: true,
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      autorestart: true,
      max_restarts: 20,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx-signals-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx-signals-error.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
    {
      name: "pumpx-trend",
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/pumpx_trend_engine.py",
      interpreter: "C:/CryptoTrader/next_version/crypto-signals/.venv-ml/Scripts/pythonw.exe",
      windowsHide: true,
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      autorestart: true,
      max_restarts: 20,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx-trend-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpx-trend-error.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
    {
      name: "pumpfun-ingest",
	  
      script: "C:/CryptoTrader/next_version/crypto-signals/ml/data_ingestion/ingest_pumpfun_live.py",
      interpreter: "C:/CryptoTrader/next_version/crypto-signals/.venv-ml/Scripts/pythonw.exe",
      windowsHide: true,
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      autorestart: true,
      max_restarts: 20,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpfun-ingest-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/pumpfun-ingest-error.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },
	  /* ----------------------- PUMPFUN STREAMER NODE  ----------------------- */
    {
      name: "PUMPFUN Wss.io socket server",
      cwd: "C:\CryptoTrader\next_version\crypto-signals\pumpx-streamer-engine",
      script: "npm",
      args: "start",
      interpreter: "C:\\Windows\\System32\\cmd.exe",
      node_args: "--max_old_space_size=2048",
      windowsHide: true,
      autorestart: true,
	  watch: true,
      max_restarts: 10,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/PUMPFUN-Wss-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/PUMPFUN-Wss-error.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },

    /* ----------------------- BACKEND NODE SERVER ----------------------- */
    {
      name: "backend-engine",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/backend-engine",
      script: "npm",
      args: "start",
      interpreter: "C:\\Windows\\System32\\cmd.exe",
      node_args: "--max_old_space_size=2048",
      windowsHide: true,
      autorestart: true,
	  watch: true,
      max_restarts: 10,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/backend-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/backend-error.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    },

    /* ----------------------- FRONTEND DEV SERVER ----------------------- */
    {
      name: "frontend-engine",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/frontend-engine",
      script: "npm",
      args: "start",
      interpreter: "C:\\Windows\\System32\\cmd.exe",
      node_args: "--max_old_space_size=4096",
      windowsHide: true,
      autorestart: true,
	  watch: true,
      max_restarts: 10,
      out_file: "C:/CryptoTrader/next_version/crypto-signals/logs/frontend-out.log",
      error_file: "C:/CryptoTrader/next_version/crypto-signals/logs/frontend-error.log",
      merge_logs: true,
	  disable_monitoring: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    }
  ]
};
