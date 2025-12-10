
ML v2 Upgrade Package

Includes:
- ml-engine/feature_builder_v2.py
  Builds enriched feature matrix using:
    * xrp_btc_hourly_spread (spread, volumes, rolling stats)
    * futures_transactions (BTC/XRP long/short notional per hour)
    * wallet_activity (tx count + notional per hour)
    * time-of-day and day-of-week encodings

- ml-engine/train_transformer_v2.py
  New training script using SpreadModelV2:
    * batch_first TransformerEncoder
    * joint Gaussian regression (mu, sigma) for 1h/4h/24h deltas
    * direction classification loss (prob_up vs prob_down)
    * time-based dataset, 80/20 temporal split

- ml-engine/services/predictor-service/main_v2.py
  New predictor service:
    * /predict_v2 endpoint (also mapped to /predict for compatibility)
    * uses feature_builder_v2 to build latest window
    * loads SpreadModelV2 from TRANSFORMER_MODEL_PATH
    * outputs mu, sigma, calibrated prob_up/prob_down

- verify_market_data.py
  Helper script to validate that downloaded candles in market_candles
  are for the expected symbols (BTCUSDT and XRPUSDT for 1h interval).

How to integrate:
1. Copy ml-engine/feature_builder_v2.py into your project under ml-engine/.
2. Copy ml-engine/train_transformer_v2.py into ml-engine/.
3. Copy ml-engine/services/predictor-service/main_v2.py into that service folder.
   Option A: change your service launcher to use main_v2.py.
   Option B: merge its code into your existing main.py.
4. Ensure TRANSFORMER_MODEL_PATH in .env points to a v2 model file, e.g.
   ./ml-engine/models/transformer_pg_model_v2.pth
5. Run:
   - python ml-engine/train_transformer_v2.py
   to train and save the v2 model.
6. Restart predictor-service so it loads the new model.
7. Run verify_market_data.py once to confirm that only BTCUSDT and XRPUSDT
   are present as 1h candles in market_candles.
