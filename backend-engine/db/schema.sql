-- backend/db/schema.sql

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) UNIQUE NOT NULL,        -- e.g. BTCUSDT
    name VARCHAR(100) NOT NULL,                -- e.g. Bitcoin / Tether
    base_asset VARCHAR(50),
    quote_asset VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS timeframes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,          -- e.g. 1m, 5m, 15m, 1h, 4h, 1d
    granularity_minutes INT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,                -- e.g. "short_term_v1"
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TYPE signal_direction AS ENUM ('BUY', 'SELL', 'HOLD');

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    timeframe_id INT NOT NULL REFERENCES timeframes(id) ON DELETE CASCADE,
    model_version_id INT REFERENCES model_versions(id) ON DELETE SET NULL,
    direction signal_direction NOT NULL,
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    entry_price NUMERIC(18,8),
    stop_loss NUMERIC(18,8),
    take_profit NUMERIC(18,8),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_asset_timeframe_created
    ON signals (asset_id, timeframe_id, created_at DESC);

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asset_id INT REFERENCES assets(id) ON DELETE SET NULL,
    timeframe_id INT REFERENCES timeframes(id) ON DELETE SET NULL,
    min_confidence NUMERIC(5,4) NOT NULL DEFAULT 0.7,
    channel_type VARCHAR(50) NOT NULL,         -- e.g. TELEGRAM, EMAIL, WEBHOOK
    channel_address VARCHAR(255) NOT NULL,     -- username/email/webhook URL
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Basic seed data (optional)
INSERT INTO timeframes (code, granularity_minutes) VALUES
    ('5m', 5),
    ('15m', 15),
    ('1h', 60),
    ('4h', 240),
    ('1d', 1440)
ON CONFLICT (code) DO NOTHING;
