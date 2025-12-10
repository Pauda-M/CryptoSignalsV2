module.exports = {
  apps: [
    {
      name: "pumpfun-ingest",
      cwd: "C:/CryptoTrader/next_version/crypto-signals",
      script: "ml/data_ingestion/ingest_pumpfun_live.py",
      interpreter: "C:/CryptoTrader/next_version/crypto-signals/ml/.venv-ml/Scripts/pythonw.exe",
      autorestart: true,
      restart_delay: 5000
    },
    {
      name: "pumpx-streamer",
      cwd: "C:/CryptoTrader/next_version/crypto-signals/pumpx-streamer-engine",
      script: "src/server.js",
      node_args: "",
      autorestart: true,
      restart_delay: 3000,
      env: 	{
        PUMPX_STREAMER_PORT: 4101,
        PGHOST: "localhost",
        PGPORT: "5432",
        PGUSER: "postgres",
        PGPASSWORD: "KarmaKoma2024",
        PGDATABASE: "crypto_signals"
			}
	},

  ]
};
